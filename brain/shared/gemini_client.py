import os
import json
import logging
import httpx
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


logger = logging.getLogger("gemini_client")

FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-flash-latest",
]


class GeminiClient:
    """
    Production-grade Google Gemini API Client.
    Supports real-time Gemini Flash inference with automatic fail-safe fallback
    across models and deterministic engine when quota or network issues occur.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.6-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Calls the real Google Gemini API asynchronously.
        Falls back gracefully if no API key is provided or quotas are reached.
        """
        if os.getenv("OFFLINE_MODE") == "1":
            return ""

        api_key = self.api_key or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            logger.info("No GEMINI_API_KEY found in environment. Using deterministic fallback engine.")
            return ""

        headers = {"Content-Type": "application/json"}
        contents = []
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System Instruction: {system_prompt}\n\nTask: {prompt}"}]
            })
        else:
            contents.append({
                "role": "user",
                "parts": [{"text": prompt}]
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024
            }
        }

        # Try primary model first, followed by fallback models on 429/503/404
        models_to_try = [self.model] + [m for m in FALLBACK_MODELS if m != self.model]

        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload, headers=headers)

                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts and "text" in parts[0]:
                                return parts[0]["text"].strip()
                    elif resp.status_code in (429, 503, 404):
                        logger.warning(f"Gemini API model '{model_name}' returned status {resp.status_code}. Attempting next fallback model...")
                        continue
                    else:
                        logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text}")
                        break
            except Exception as e:
                logger.warning(f"Gemini API invocation error on '{model_name}': {e}.")
                continue

        return ""

    async def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Requests structured JSON from Gemini and safely parses output.
        """
        json_instruction = (
            "You MUST respond ONLY with a valid, raw JSON object. "
            "Do NOT include markdown formatting, backticks (```json), or explanatory text."
        )
        sys_full = f"{system_prompt or ''}\n\n{json_instruction}".strip()
        raw = await self.generate_text(prompt, system_prompt=sys_full)
        if not raw:
            return None

        # Clean markdown code blocks if returned
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"Failed to parse Gemini JSON output: {e}. Raw was: {raw}")
            return None

gemini_client = GeminiClient()
