from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from apps.api.database import get_db
from apps.api.models import AgentRun, ActionProposal
from apps.api.schemas import AgentRunResponse

router = APIRouter(prefix="/agents", tags=["Agents"])

AGENT_REGISTRY = [
    {"id": "inventory",   "name": "Inventory Agent",     "emoji": "📦", "domain": "Stock & Replenishment"},
    {"id": "pricing",     "name": "Pricing Agent",        "emoji": "💰", "domain": "Margin Optimization"},
    {"id": "support",     "name": "Support Agent",        "emoji": "💬", "domain": "RAG Customer Service"},
    {"id": "order_ops",   "name": "Order Ops Agent",      "emoji": "🚚", "domain": "Fulfillment Rules"},
    {"id": "logistics",   "name": "Logistics Agent",      "emoji": "🛩",  "domain": "Carrier Scorecards"},
    {"id": "marketing",   "name": "Marketing Agent",      "emoji": "📢", "domain": "Ad Spend Protection"},
    {"id": "supervisor",  "name": "Master Orchestrator",  "emoji": "🎯", "domain": "Cross-Agent Coordination"},
]


@router.get("/health")
async def get_agents_health(db: AsyncSession = Depends(get_db)):
    """
    Returns real-time heartbeat status for all 7 agents.
    An agent is 'online' if it has a run record in the last 60 minutes.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=1)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    health = []
    for agent in AGENT_REGISTRY:
        latest_res = await db.execute(
            select(AgentRun)
            .where(AgentRun.agent_name.ilike(f"%{agent['id']}%"))
            .order_by(AgentRun.started_at.desc())
            .limit(1)
        )
        latest = latest_res.scalar_one_or_none()

        count_res = await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.agent_name.ilike(f"%{agent['id']}%"),
                AgentRun.started_at >= today_start
            )
        )
        runs_today = count_res.scalar() or 0

        last_seen = latest.started_at if latest else None
        is_online = (
            latest and last_seen and
            last_seen.replace(tzinfo=timezone.utc) >= cutoff
        )

        health.append({
            "id": agent["id"],
            "name": agent["name"],
            "emoji": agent["emoji"],
            "domain": agent["domain"],
            "status": "online" if is_online else ("idle" if latest else "standby"),
            "last_seen": last_seen.isoformat() if last_seen else None,
            "runs_today": runs_today,
            "last_status": latest.status if latest else "never_run",
            "last_latency_ms": latest.latency_ms if latest else None,
        })

    total_online = sum(1 for a in health if a["status"] == "online")
    return {
        "agents": health,
        "total": len(health),
        "online_count": total_online,
        "hive_status": "active" if total_online > 0 else "standby",
        "checked_at": now.isoformat(),
    }


@router.get("/runs", response_model=List[AgentRunResponse])
async def get_agent_runs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)
    )
    runs = result.scalars().all()
    out = []
    for r in runs:
        out.append(
            AgentRunResponse(
                id=r.id,
                agent_name=r.agent_name,
                status=r.status,
                confidence=float(r.confidence or 0.95),
                summary=r.result.get("summary") if r.result else None,
                latency_ms=r.latency_ms or 120,
                tokens_input=r.tokens_input,
                tokens_output=r.tokens_output,
                started_at=r.started_at,
                completed_at=r.completed_at,
                actions=[]
            )
        )
    return out


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_agent_run_detail(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Agent run not found")

    actions_res = await db.execute(
        select(ActionProposal).where(ActionProposal.agent_run_id == run_id)
    )
    actions = actions_res.scalars().all()

    return AgentRunResponse(
        id=r.id,
        agent_name=r.agent_name,
        status=r.status,
        confidence=float(r.confidence or 0.95),
        summary=r.result.get("summary") if r.result else None,
        latency_ms=r.latency_ms or 120,
        tokens_input=r.tokens_input,
        tokens_output=r.tokens_output,
        started_at=r.started_at,
        completed_at=r.completed_at,
        actions=[
            {
                "id": a.id,
                "tenant_id": a.tenant_id,
                "agent_run_id": a.agent_run_id,
                "action_type": a.action_type,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "parameters": a.parameters,
                "risk_level": a.risk_level,
                "status": a.status,
                "requires_approval": a.requires_approval,
                "summary": a.summary,
                "evidence": a.evidence,
                "policy_result": a.policy_result,
                "created_at": a.created_at
            }
            for a in actions
        ]
    )
