from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from apps.api.database import get_db

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/live")
async def liveness():
    return {"status": "ok", "service": "ecom-ai-api", "timestamp": "live"}

@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "degraded", "database": str(e)}
