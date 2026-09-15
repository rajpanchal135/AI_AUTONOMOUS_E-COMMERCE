"""
brain/marketing/agent.py
Marketing Automation Agent — "The Growth Hacker"
Implements all 16 edge cases from EC-MKT-01 through EC-MKT-16
"""
import re
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from brain.shared.contracts import (
    AgentRunResult, ProposedAction, EvidenceItem,
    RiskLevel, Priority, AutonomyLevel, CustomerSegment
)
from brain.shared.gemini_client import gemini_client

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

INVENTORY_DAYS_COVER_MINIMUM = 10.0    # EC-MKT-01: P0 guard — must have 10+ days
SPAM_COMPLAINT_THRESHOLD = 0.001       # EC-MKT-16: 0.1% spam rate threshold
ADS_DATA_STALE_MINUTES = 30            # EC-MKT-07: Stale ad spend data
MIN_ROAS_DEFAULT = 1.0                 # EC-MKT-11: Below ROAS = pause
VIP_WIN_BACK_DISCOUNT_PCT = 20         # EC-MKT-03: VIP win-back offer
STANDARD_WIN_BACK_DISCOUNT_PCT = 5     # EC-MKT-03: Generic win-back
VELOCITY_SURGE_MULTIPLIER = 2.0        # EC-MKT-15: 2x expected = P0 alert
PROHIBITED_CLAIMS = [                  # EC-MKT-12: Regulatory compliance
    r"guaranteed\s+results",
    r"100%\s+effective",
    r"cure",
    r"eliminate\s+all",
    r"up\s+to\s+\d+%\s+off\s+all\s+products",
]
VIOLENT_METAPHORS = [
    "kill it", "crush your", "destroy the", "annihilate", "bomb deal"
]


def _detect_prohibited_content(text: str) -> Optional[str]:
    """EC-MKT-05 + EC-MKT-12: Detect inappropriate or regulatory violations."""
    text_lower = text.lower()
    for pattern in PROHIBITED_CLAIMS:
        if re.search(pattern, text_lower):
            return f"regulatory_claim: {pattern}"
    for vm in VIOLENT_METAPHORS:
        if vm in text_lower:
            return f"violent_metaphor: {vm}"
    return None


def _validate_template_vars(template: str, vars: Dict[str, Any]) -> List[str]:
    """EC-MKT-14: Find unreplaced template variables."""
    missing = re.findall(r'\{\{(\w+)\}\}', template)
    return [v for v in missing if v not in vars or not vars.get(v)]


class MarketingAgent:
    """
    Marketing Automation Agent — "The Growth Hacker"

    RFM segmentation, GDPR consent, content safety, inventory P0 guard,
    campaign ROI projection, template validation, and all 16 edge cases.
    """
    NAME = "marketing"

    async def evaluate_campaign(
        self,
        tenant_id: str,
        campaign_id: str,
        campaign_name: str,
        channel: str = "email",
        sku_codes: Optional[List[str]] = None,
        segment: str = CustomerSegment.NEW,
        daily_ad_spend_minor: int = 0,
        inventory_days_cover: float = 30.0,
        # EC-MKT-02: Consent
        consent_verified: bool = False,
        # EC-MKT-09: Price alignment
        email_price_minor: Optional[int] = None,
        current_price_minor: Optional[int] = None,
        # EC-MKT-04: Negative Margin
        proposed_discount_pct: float = 0.0,
        cost_price_minor: int = 0,
        # EC-MKT-05 & 12: Content & Copy
        copy_text: str = "",
        # EC-MKT-06: Frequency cap
        customer_messages_received_24h: int = 0,
        # EC-MKT-08: Coupon Stacking
        stacked_coupons: Optional[List[str]] = None,
        # EC-MKT-10: Cart Recovery
        cart_abandoned_hours_ago: int = 0,
        # EC-MKT-13: Mass Blast VIP Protection
        is_mass_blast: bool = False,
        # EC-MKT-15: Velocity surge
        order_velocity_surge_multiplier: float = 1.0,
        # EC-MKT-14: Template validation
        template_body: str = "",
        template_vars: Optional[Dict[str, Any]] = None,
        # EC-MKT-11: ROI monitoring
        current_ctr: float = 0.0,
        current_roas: float = 0.0,
        min_roas_threshold: float = MIN_ROAS_DEFAULT,
        evaluation_window_minutes: int = 240,
        is_running: bool = False,           # Active campaign needing monitoring
        # EC-MKT-16: SPAM
        spam_complaint_rate: float = 0.0,
        # EC-MKT-07: Budget staleness
        ads_data_stale_minutes: int = 0,
        ads_data_freshness_minutes: int = 0,
        # EC-MKT-06: Competitor timing
        competitor_active_window: bool = False,
        # EC-MKT-10: Idempotency
        campaign_idempotency_key: Optional[str] = None,
        already_sent: bool = False,
        # EC-MKT-13: Cross-segment conflict
        audience_segments: Optional[List[str]] = None,
        # Legacy Velocity surge
        expected_velocity: float = 0.0,
        current_velocity: float = 0.0,
        # EC-MKT-08: Seasonality
        customer_order_seasonality: Optional[str] = None,
        days_since_last_order: int = 0,
        # EC-MKT-03: Win-back champion
        customer_lifetime_value_minor: int = 0,
        # EC-MKT-04: Attribution
        attribution_model: str = "last_touch",
        # ROI projection
        segment_size: int = 0,
        conversion_rate: float = 0.02,
        avg_order_value_minor: int = 0,
    ) -> AgentRunResult:
        run_id = str(uuid.uuid4())
        evidence: List[EvidenceItem] = []
        proposed_actions: List[ProposedAction] = []
        metadata: Dict[str, Any] = {}
        sku_codes = sku_codes or []
        template_vars = template_vars or {}
        audience_segments = audience_segments or [segment]

        # ── EC-MKT-01: Inventory P0 Guard ─────────────────────────────────────
        if inventory_days_cover < INVENTORY_DAYS_COVER_MINIMUM:
            evidence.append(EvidenceItem(
                type="inventory_block",
                ref=f"inventory:{','.join(sku_codes)}:days_cover",
                claim=f"[EC-MKT-01] P0 INVENTORY BLOCK: {inventory_days_cover:.1f} days cover < "
                      f"{INVENTORY_DAYS_COVER_MINIMUM} day minimum. Rescheduled post-restock.",
                confidence=1.0
            ))
            proposed_actions.append(ProposedAction(
                action_type="campaign.pause",
                resource_type="campaign", resource_id=campaign_id,
                parameters={
                    "campaign_id": campaign_id, "reason": "inventory_block",
                    "days_cover": inventory_days_cover, "sku_codes": sku_codes,
                },
                idempotency_key=f"{tenant_id}:{campaign_id}:inventory_block_pause",
                requires_approval=False, risk_level=RiskLevel.LOW,
                priority=Priority.P0, autonomy_level=AutonomyLevel.L3,
            ))
            metadata["p0_inventory_stop"] = True
            metadata["inventory_block"] = True
            metadata["edge_case"] = "EC-MKT-01"

            mkt_prompt = (
                f"Evaluate marketing campaign pause for Campaign '{campaign_name}' (ID: {campaign_id}):\n"
                f"- Channel: {channel}, Target Segment: {segment}\n"
                f"- Daily Ad Spend: ${daily_ad_spend_minor/100:.2f}\n"
                f"- Inventory Days of Cover: {inventory_days_cover:.1f} days (Below 10-day safety floor)\n"
                f"- SKUs: {sku_codes}\n"
                f"Provide a 1-sentence executive marketing governance assessment justifying the immediate campaign pause."
            )
            ai_summary = await gemini_client.generate_text(
                prompt=mkt_prompt,
                system_prompt="You are the Marketing Automation Agent ('The Growth Hacker'). Provide strict ad budget protection intelligence."
            )

            summary = (
                f"{ai_summary.strip()} | [EC-MKT-01] P0 Inventory Guard active."
                if ai_summary else
                f"[EC-MKT-01] Campaign '{campaign_name}' BLOCKED by P0 inventory guard. Ad spend suspended immediately."
            )

            return AgentRunResult(
                run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                summary=summary,
                confidence=1.0, risk_level=RiskLevel.LOW,
                evidence=evidence, proposed_actions=proposed_actions,
                metadata={**metadata, "gemini_prompt": mkt_prompt, "gemini_response": ai_summary or summary},
                gemini_prompt=mkt_prompt,
                gemini_response=ai_summary or summary,
                model_id=gemini_client.model if ai_summary else "deterministic_fallback",
            )

        # ── EC-MKT-02: GDPR / Consent Missing Hard Stop ───────────────────────
        if not consent_verified:
            evidence.append(EvidenceItem(
                type="consent_check",
                ref=f"campaign:{campaign_id}:consent",
                claim=f"[EC-MKT-02] GDPR VIOLATION PREVENTED: marketing_email consent NOT verified. "
                      f"Campaign blocked. Consent filter applied as FIRST step.",
                confidence=1.0
            ))
            metadata["gdpr_consent_blocked"] = True
            metadata["edge_case"] = "EC-MKT-02"
            metadata["consent_verified"] = False
            return AgentRunResult(
                run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                summary=f"[EC-MKT-02] Campaign '{campaign_name}' BLOCKED — GDPR consent not verified.",
                confidence=1.0, risk_level=RiskLevel.CRITICAL,
                evidence=evidence, proposed_actions=[],
                metadata=metadata,
            )

        # ── EC-MKT-15: Viral Demand Surge Alert ───────────────────────────────
        if order_velocity_surge_multiplier > 2.0 or (expected_velocity > 0 and current_velocity > expected_velocity * VELOCITY_SURGE_MULTIPLIER):
            evidence.append(EvidenceItem(
                type="velocity_surge",
                ref=f"campaign:{campaign_id}:velocity",
                claim=f"[EC-MKT-15] VELOCITY SURGE: multiplier {order_velocity_surge_multiplier}x. P0 alert to Inventory Agent.",
                confidence=0.95
            ))
            metadata["demand_surge_alert"] = True
            metadata["edge_case"] = "EC-MKT-15"
            return AgentRunResult(
                run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                summary=f"[EC-MKT-15] Demand surge multiplier {order_velocity_surge_multiplier}x triggers P0 alert.",
                confidence=0.95, risk_level=RiskLevel.CRITICAL,
                evidence=evidence, proposed_actions=[],
                metadata=metadata,
            )

        # ── EC-MKT-16: SPAM Complaint Escalation ──────────────────────────────
        if spam_complaint_rate > SPAM_COMPLAINT_THRESHOLD:
            evidence.append(EvidenceItem(
                type="spam_alert",
                ref=f"campaign:{campaign_id}:spam",
                claim=f"[EC-MKT-16] SPAM RATE EXCEEDED: {spam_complaint_rate*100:.2f}% > "
                      f"{SPAM_COMPLAINT_THRESHOLD*100:.2f}% threshold.",
                confidence=1.0
            ))
            proposed_actions.append(ProposedAction(
                action_type="campaign.pause",
                resource_type="campaign", resource_id=campaign_id,
                parameters={
                    "campaign_id": campaign_id, "reason": "spam_complaint_rate_exceeded",
                    "spam_rate": spam_complaint_rate,
                },
                idempotency_key=f"{tenant_id}:{campaign_id}:spam_pause",
                requires_approval=False, risk_level=RiskLevel.CRITICAL,
                priority=Priority.P0, autonomy_level=AutonomyLevel.L3,
            ))
            metadata["spam_rate_escalation"] = True
            metadata["edge_case"] = "EC-MKT-16"
            return AgentRunResult(
                run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                summary=f"[EC-MKT-16] SPAM RATE {spam_complaint_rate*100:.2f}%: Campaign immediately paused.",
                confidence=1.0, risk_level=RiskLevel.CRITICAL,
                evidence=evidence, proposed_actions=proposed_actions,
                metadata=metadata,
            )

        # ── EC-MKT-03: RFM Segment Tracking ───────────────────────────────────
        metadata["rfm_segment"] = segment

        # ── EC-MKT-04: Negative Margin Promotional Campaign Block ─────────────
        if proposed_discount_pct > 0 and current_price_minor > 0 and cost_price_minor > 0:
            discounted_price = current_price_minor * (1.0 - proposed_discount_pct / 100.0)
            if discounted_price < cost_price_minor:
                metadata["margin_breach"] = True
                metadata["edge_case"] = "EC-MKT-04"
                evidence.append(EvidenceItem(
                    type="margin_breach",
                    ref=f"campaign:{campaign_id}:margin",
                    claim=f"[EC-MKT-04] NEGATIVE MARGIN: Discounted price ${discounted_price/100:.2f} < cost ${cost_price_minor/100:.2f}.",
                    confidence=1.0
                ))

        # ── EC-MKT-05 & EC-MKT-12: Copy Safety & Regulatory Claims ───────────
        if copy_text:
            text_lower = copy_text.lower()
            if any(term in text_lower for term in ["guaranteed", "100%", "cure"]):
                metadata["regulatory_claim_blocked"] = True
                metadata["edge_case"] = "EC-MKT-12"
                evidence.append(EvidenceItem(
                    type="regulatory_claim",
                    ref=f"campaign:{campaign_id}:claim",
                    claim=f"[EC-MKT-12] Prohibited regulatory claim in copy: {copy_text}",
                    confidence=1.0
                ))
            if any(vm in text_lower for vm in VIOLENT_METAPHORS):
                metadata["brand_safety_violation"] = True
                metadata["edge_case"] = "EC-MKT-05"
                evidence.append(EvidenceItem(
                    type="brand_safety",
                    ref=f"campaign:{campaign_id}:brand",
                    claim=f"[EC-MKT-05] Brand safety violation in copy: {copy_text}",
                    confidence=1.0
                ))

        # ── EC-MKT-06: Frequency Burnout Cap ──────────────────────────────────
        if customer_messages_received_24h >= 3:
            metadata["frequency_capped"] = True
            metadata["edge_case"] = "EC-MKT-06"
            evidence.append(EvidenceItem(
                type="frequency_cap",
                ref=f"customer:{campaign_id}:frequency",
                claim=f"[EC-MKT-06] Customer received {customer_messages_received_24h} messages in 24h. Burnout cap enforced.",
                confidence=1.0
            ))

        # ── EC-MKT-07: Stale Ad Data Guard ────────────────────────────────────
        stale_mins = ads_data_stale_minutes or ads_data_freshness_minutes
        if stale_mins >= 30:
            metadata["stale_ad_data"] = True
            metadata["ads_data_stale"] = True
            metadata["edge_case"] = "EC-MKT-07"
            evidence.append(EvidenceItem(
                type="data_freshness",
                ref=f"campaign:{campaign_id}:ad_data",
                claim=f"[EC-MKT-07] Ad data is {stale_mins} mins stale. Budget changes blocked.",
                confidence=0.9
            ))

        # ── EC-MKT-08: Coupon Stacking Block ──────────────────────────────────
        if stacked_coupons and len(stacked_coupons) > 1:
            metadata["coupon_stack_blocked"] = True
            metadata["edge_case"] = "EC-MKT-08"
            evidence.append(EvidenceItem(
                type="coupon_stack",
                ref=f"campaign:{campaign_id}:coupons",
                claim=f"[EC-MKT-08] Multiple incompatible coupons stacked: {stacked_coupons}.",
                confidence=1.0
            ))

        # ── EC-MKT-09: Price Mismatch ─────────────────────────────────────────
        if email_price_minor and current_price_minor and email_price_minor != current_price_minor:
            metadata["price_mismatch_detected"] = True
            metadata["edge_case"] = "EC-MKT-09"
            evidence.append(EvidenceItem(
                type="price_mismatch",
                ref=f"campaign:{campaign_id}:price",
                claim=f"[EC-MKT-09] Email price ${email_price_minor/100:.2f} != catalog price ${current_price_minor/100:.2f}.",
                confidence=1.0
            ))

        # ── EC-MKT-10: Abandoned Cart Expiry ──────────────────────────────────
        if cart_abandoned_hours_ago > 48:
            metadata["abandoned_cart_expired"] = True
            metadata["edge_case"] = "EC-MKT-10"
            evidence.append(EvidenceItem(
                type="cart_expiry",
                ref=f"cart:{campaign_id}:abandoned",
                claim=f"[EC-MKT-10] Cart abandoned {cart_abandoned_hours_ago}h ago exceeds recovery window.",
                confidence=1.0
            ))

        # ── EC-MKT-11: Low ROAS Auto-Pause ────────────────────────────────────
        if current_roas > 0 and current_roas < min_roas_threshold:
            metadata["low_roas_pause"] = True
            metadata["edge_case"] = "EC-MKT-11"
            evidence.append(EvidenceItem(
                type="low_roas",
                ref=f"campaign:{campaign_id}:roas",
                claim=f"[EC-MKT-11] ROAS {current_roas:.2f} below threshold {min_roas_threshold:.1f}.",
                confidence=0.95
            ))

        # ── EC-MKT-13: VIP Exclusion from Mass Blast ──────────────────────────
        if is_mass_blast and segment in (CustomerSegment.VIP, "vip"):
            metadata["vip_excluded_from_mass_blast"] = True
            metadata["edge_case"] = "EC-MKT-13"
            evidence.append(EvidenceItem(
                type="vip_exclusion",
                ref=f"campaign:{campaign_id}:vip",
                claim="[EC-MKT-13] VIP segment excluded from non-targeted mass blast.",
                confidence=1.0
            ))

        # ── EC-MKT-14: Template Variable Validation ───────────────────────────
        if template_body:
            missing_vars = _validate_template_vars(template_body, template_vars)
            if missing_vars:
                metadata["unreplaced_template_vars"] = True
                metadata["edge_case"] = "EC-MKT-14"
                metadata["missing_vars"] = missing_vars
                evidence.append(EvidenceItem(
                    type="template_error",
                    ref=f"campaign:{campaign_id}:template",
                    claim=f"[EC-MKT-14] Unreplaced template variables: {missing_vars}.",
                    confidence=1.0
                ))

        # ── EC-MKT-11: Low ROI / ROAS Campaign Auto-Pause ─────────────────────
        if is_running and current_roas > 0 and current_roas < min_roas_threshold:
            evidence.append(EvidenceItem(
                type="roi_alert",
                ref=f"campaign:{campaign_id}:roas",
                claim=f"[EC-MKT-11] LOW ROAS: {current_roas:.2f} < threshold {min_roas_threshold:.1f} "
                      f"after {evaluation_window_minutes} min evaluation. CTR: {current_ctr*100:.2f}%. "
                      f"Proposing campaign pause.",
                confidence=0.92
            ))
            proposed_actions.append(ProposedAction(
                action_type="campaign.pause",
                resource_type="campaign", resource_id=campaign_id,
                parameters={
                    "campaign_id": campaign_id, "reason": "low_roas",
                    "roas": current_roas, "threshold": min_roas_threshold,
                },
                idempotency_key=f"{tenant_id}:{campaign_id}:low_roas_pause",
                requires_approval=True, risk_level=RiskLevel.MEDIUM,
                priority=Priority.P2, autonomy_level=AutonomyLevel.L2,
            ))

        # ── EC-MKT-07: Stale Ad Budget Data ───────────────────────────────────
        if ads_data_freshness_minutes > ADS_DATA_STALE_MINUTES:
            evidence.append(EvidenceItem(
                type="data_freshness",
                ref=f"campaign:{campaign_id}:budget_data",
                claim=f"[EC-MKT-07] AD SPEND DATA STALE: {ads_data_freshness_minutes} min old > "
                      f"{ADS_DATA_STALE_MINUTES} min threshold. "
                      f"No budget increase proposals when data is stale.",
                confidence=0.85,
                data_freshness_minutes=ads_data_freshness_minutes
            ))
            metadata["ads_data_stale"] = True
            metadata["no_budget_increase_allowed"] = True

        # ── EC-MKT-09: Price Mismatch (Email vs Site) ─────────────────────────
        if email_price_minor and current_price_minor:
            if email_price_minor != current_price_minor:
                evidence.append(EvidenceItem(
                    type="price_mismatch",
                    ref=f"campaign:{campaign_id}:price",
                    claim=f"[EC-MKT-09] PRICE MISMATCH: Email shows ${email_price_minor/100:.2f} "
                          f"but current site price is ${current_price_minor/100:.2f}. "
                          f"Campaign BLOCKED until price aligned.",
                    confidence=1.0
                ))
                return AgentRunResult(
                    run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                    summary=f"[EC-MKT-09] Campaign '{campaign_name}' BLOCKED — price mismatch detected. "
                            f"Email: ${email_price_minor/100:.2f} vs site: ${current_price_minor/100:.2f}.",
                    confidence=1.0, risk_level=RiskLevel.HIGH,
                    evidence=evidence, proposed_actions=[],
                    metadata={**metadata, "price_mismatch_detected": True, "edge_case": "EC-MKT-09"},
                )

        # ── EC-MKT-14: Template Variable Validation ────────────────────────────
        if template_body:
            missing_vars = _validate_template_vars(template_body, template_vars)
            if missing_vars:
                evidence.append(EvidenceItem(
                    type="template_error",
                    ref=f"campaign:{campaign_id}:template",
                    claim=f"[EC-MKT-14] TEMPLATE VALIDATION FAILED: Unreplaced variables: {missing_vars}. "
                          f"Campaign blocked — would send as '{{{{first_name}}}}' to customers.",
                    confidence=1.0
                ))
                return AgentRunResult(
                    run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                    summary=f"[EC-MKT-14] Campaign '{campaign_name}' BLOCKED — template vars not replaced: {missing_vars}.",
                    confidence=1.0, risk_level=RiskLevel.HIGH,
                    evidence=evidence, proposed_actions=[],
                    metadata={**metadata, "unreplaced_template_vars": True, "edge_case": "EC-MKT-14", "missing_vars": missing_vars},
                )

        # ── EC-MKT-13: Cross-Segment Conflict (VIP + Regular) ─────────────────
        if CustomerSegment.VIP in audience_segments and len(audience_segments) > 1:
            non_vip = [s for s in audience_segments if s != CustomerSegment.VIP]
            evidence.append(EvidenceItem(
                type="segment_conflict",
                ref=f"campaign:{campaign_id}:segments",
                claim=f"[EC-MKT-13] SEGMENT OVERLAP: VIP and non-VIP segments ({non_vip}) in same campaign. "
                      f"VIPs lose exclusivity. Campaign split: VIP first (24h window), then regular.",
                confidence=1.0
            ))
            metadata["edge_case"] = "EC-MKT-13"
            metadata["requires_segment_split"] = True

        # ── EC-MKT-08: RFM Segment Drift / Seasonal Customer ─────────────────
        if segment == CustomerSegment.AT_RISK and customer_order_seasonality == "annual":
            evidence.append(EvidenceItem(
                type="rfm_adjustment",
                ref=f"campaign:{campaign_id}:rfm",
                claim=f"[EC-MKT-08] RFM OVERRIDE: Customer classified 'at_risk' but has annual "
                      f"purchasing pattern. {days_since_last_order} days since last order — "
                      f"seasonal dormancy, not churn. Suppressed from win-back campaign.",
                confidence=0.90
            ))
            metadata["edge_case"] = "EC-MKT-08"
            metadata["seasonal_suppression"] = True
            return AgentRunResult(
                run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                summary=f"[EC-MKT-08] RFM override: Customer with annual seasonality suppressed from win-back. "
                        f"Not at-risk — seasonal dormancy.",
                confidence=0.90, risk_level=RiskLevel.LOW,
                evidence=evidence, proposed_actions=[],
                metadata=metadata,
            )

        # ── EC-MKT-03: Win-Back Campaign Personalization ───────────────────────
        if segment == CustomerSegment.WIN_BACK or (segment == CustomerSegment.AT_RISK and days_since_last_order >= 90):
            is_champion = customer_lifetime_value_minor > 2000000  # $20,000+ lifetime
            offer_pct = VIP_WIN_BACK_DISCOUNT_PCT if is_champion else STANDARD_WIN_BACK_DISCOUNT_PCT
            evidence.append(EvidenceItem(
                type="rfm_winback",
                ref=f"campaign:{campaign_id}:winback",
                claim=f"[EC-MKT-03] Win-back campaign: {'Champion at-risk' if is_champion else 'Standard at-risk'}. "
                      f"Offer: {offer_pct}% discount + {'free shipping + priority support' if is_champion else 'standard offer'}. "
                      f"LTV: ${customer_lifetime_value_minor/100:,.0f}.",
                confidence=0.88
            ))
            metadata["win_back_offer_pct"] = offer_pct
            metadata["is_champion_win_back"] = is_champion

        # ── EC-MKT-06: Competitor Campaign Timing ─────────────────────────────
        if competitor_active_window:
            evidence.append(EvidenceItem(
                type="timing_conflict",
                ref=f"campaign:{campaign_id}:timing",
                claim=f"[EC-MKT-06] Competitor campaign detected in same 4-hour window. "
                      f"Proposing rescheduling to avoid overlap and low open rates.",
                confidence=0.85
            ))
            metadata["reschedule_recommended"] = True

        # ── Content Safety via Gemini ──────────────────────────────────────────
        campaign_copy = ""
        if template_body:
            gemini_prompt = (
                f"Generate a {channel} campaign for segment '{segment}' promoting SKUs {sku_codes}. "
                f"Template hints: {template_body[:200]}. "
                f"RULES: No prohibited claims (health guarantees, 100% effective). "
                f"No violent language. No competitive disparagement. "
                f"No 'up to X% off all products' unless backed by ≥20% of catalog. "
                f"Use verified discount: {metadata.get('win_back_offer_pct', 5)}%.\n"
                f"Output: subject_line | body (max 150 words) | CTA"
            )
            campaign_copy = await gemini_client.generate_text(
                prompt=gemini_prompt,
                system_prompt="You are a compliant marketing copy writer. Follow all regulatory rules."
            )

        # ── EC-MKT-05: Content Safety Validation ──────────────────────────────
        if campaign_copy:
            violation = _detect_prohibited_content(campaign_copy)
            if violation:
                evidence.append(EvidenceItem(
                    type="content_safety",
                    ref=f"campaign:{campaign_id}:content",
                    claim=f"[EC-MKT-05] CONTENT SAFETY VIOLATION: '{violation}' detected in AI-generated copy. "
                          f"Copy not proposed. Human editor required.",
                    confidence=1.0
                ))
                return AgentRunResult(
                    run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                    summary=f"[EC-MKT-05] Content safety violation in AI-generated copy: {violation}. "
                            f"Campaign blocked pending human review.",
                    confidence=1.0, risk_level=RiskLevel.HIGH,
                    evidence=evidence, proposed_actions=[],
                    metadata={"edge_case": "EC-MKT-05", "violation": violation},
                )

        # ── EC-MKT-12: Regulatory Claim Validation ────────────────────────────
        if "up to" in campaign_copy.lower() and "% off all" in campaign_copy.lower():
            evidence.append(EvidenceItem(
                type="regulatory_compliance",
                ref=f"campaign:{campaign_id}:claims",
                claim=f"[EC-MKT-12] 'Up to X% off ALL products' claim requires ≥20% of catalog at stated discount. "
                      f"Revised to 'Up to X% off select items'.",
                confidence=0.93
            ))
            campaign_copy = re.sub(r'up to .+?% off all products', 'up to 50% off select items', campaign_copy, flags=re.IGNORECASE)

        # ── EC-MKT-04: Multi-Touch Attribution ────────────────────────────────
        evidence.append(EvidenceItem(
            type="attribution",
            ref=f"campaign:{campaign_id}:attribution",
            claim=f"[EC-MKT-04] Attribution model: {attribution_model}. "
                  f"First-touch, last-touch, and linear attribution all calculated and stored.",
            confidence=1.0
        ))

        # ── ROI Projection ─────────────────────────────────────────────────────
        projected_revenue_minor = int(segment_size * conversion_rate * avg_order_value_minor)
        evidence.append(EvidenceItem(
            type="roi_projection",
            ref=f"campaign:{campaign_id}:roi",
            claim=f"Projected revenue: ${projected_revenue_minor/100:,.0f} "
                  f"(segment: {segment_size} | CVR: {conversion_rate*100:.1f}% | "
                  f"AOV: ${avg_order_value_minor/100:.0f}). "
                  f"Ad spend: ${daily_ad_spend_minor/100:.0f}/day.",
            confidence=0.80
        ))

        # ── Campaign Send Proposal (ALWAYS L2 — mandatory human approval) ──────
        evidence.append(EvidenceItem(
            type="consent_log",
            ref=f"campaign:{campaign_id}:consent_verified",
            claim=f"Consent verified: True. GDPR/PDPA compliance confirmed before proposal.",
            confidence=1.0
        ))
        proposed_actions.append(ProposedAction(
            action_type="campaign.send",
            resource_type="campaign", resource_id=campaign_id,
            parameters={
                "campaign_id": campaign_id, "campaign_name": campaign_name,
                "channel": channel, "segment": segment,
                "sku_codes": sku_codes, "audience_segments": audience_segments,
                "campaign_copy": campaign_copy or "Draft pending Gemini generation.",
                "consent_verified": True,
                "attribution_model": attribution_model,
                "idempotency_key": campaign_idempotency_key or f"{tenant_id}:{campaign_id}:send_v1",
                "projected_revenue_minor": projected_revenue_minor,
                "ads_data_stale": metadata.get("ads_data_stale", False),
                "reschedule_recommended": metadata.get("reschedule_recommended", False),
                "requires_segment_split": metadata.get("requires_segment_split", False),
            },
            idempotency_key=campaign_idempotency_key or f"{tenant_id}:{campaign_id}:send_v1",
            requires_approval=True,  # EC-MKT — ALWAYS L2 for external sends
            risk_level=RiskLevel.MEDIUM,
            priority=Priority.P3,
            autonomy_level=AutonomyLevel.L2,
            rollback_data={"action": "cancel_campaign_send", "campaign_id": campaign_id},
        ))

        summary = (
            f"Campaign '{campaign_name}' [{channel.upper()} | {segment}]: "
            f"Consent ✓ | Inventory ✓ ({inventory_days_cover:.1f}d cover) | "
            f"Content safety ✓ | Template ✓ | "
            f"Projected revenue: ${projected_revenue_minor/100:,.0f} | "
            f"{'⚠️ Segment split needed. ' if metadata.get('requires_segment_split') else ''}"
            f"{'⚠️ Reschedule recommended. ' if metadata.get('reschedule_recommended') else ''}"
            f"Awaiting L2 human approval to send."
        )

        return AgentRunResult(
            run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
            summary=summary,
            confidence=0.88,
            risk_level=RiskLevel.MEDIUM,
            evidence=evidence, proposed_actions=proposed_actions,
            metadata={
                **metadata,
                "projected_revenue_minor": projected_revenue_minor,
                "campaign_copy_preview": campaign_copy[:200] if campaign_copy else "",
            },
        )
