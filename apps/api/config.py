import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    
    _raw_db_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ecom_ai.db")
    if _raw_db_url.startswith("postgresql://") or _raw_db_url.startswith("postgres://"):
        _cleaned = _raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1).replace("postgres://", "postgresql+asyncpg://", 1)
        _cleaned = _cleaned.replace("sslmode=require", "ssl=require").replace("&channel_binding=require", "").replace("?channel_binding=require", "?")
        DATABASE_URL: str = _cleaned.rstrip("?").rstrip("&")
    else:
        DATABASE_URL: str = _raw_db_url

    SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL", "sqlite:///./ecom_ai.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    DEFAULT_TENANT_ID: str = os.getenv("DEFAULT_TENANT_ID", "11111111-1111-1111-1111-111111111111")
    DEFAULT_AUTONOMY_LEVEL: int = int(os.getenv("DEFAULT_AUTONOMY_LEVEL", "2"))
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    BEDROCK_REASONING_MODEL_ID: str = os.getenv("BEDROCK_REASONING_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    BEDROCK_FAST_MODEL_ID: str = os.getenv("BEDROCK_FAST_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

settings = Settings()
