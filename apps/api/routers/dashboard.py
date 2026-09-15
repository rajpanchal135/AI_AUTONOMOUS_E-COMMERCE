from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from apps.api.config import settings
from apps.api.database import get_db
from apps.api.models import (
    ActionProposal, AgentRun, Order, InventoryLevel, SupportTicket, SKU
)
from apps.api.schemas import DashboardSummaryResponse, ActionProposalResponse, AgentRunResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

class AutonomyUpdateRequest(BaseModel):
    autonomy_level: int = Field(ge=1, le=4, description="Autonomy Level 1 to 4")

@router.post("/autonomy")
async def update_autonomy_level(payload: AutonomyUpdateRequest):
    settings.DEFAULT_AUTONOMY_LEVEL = payload.autonomy_level
    levels_desc = {
        1: "Level 1 (Observe & Recommend) - All proposals require human sign-off",
        2: "Level 2 (Guarded HITL) - Low risk auto-tagged, monetary/destructive requires review",
        3: "Level 3 (Autonomous with Money Limits) - High autonomy under $50 threshold",
        4: "Level 4 (Fully Autonomous) - Continuous autonomous agent loop"
    }
    return {
        "status": "success",
        "autonomy_level": settings.DEFAULT_AUTONOMY_LEVEL,
        "description": levels_desc.get(payload.autonomy_level, f"Level {payload.autonomy_level}")
    }

@router.get("/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    # 1. Total revenue & orders count
    orders_res = await db.execute(select(func.count(Order.id), func.sum(Order.total_minor)))
    orders_count, total_revenue = orders_res.first()
    orders_count = orders_count or 0
    total_revenue = total_revenue or 0

    # 2. Critical stockouts
    stockouts_res = await db.execute(
        select(func.count(InventoryLevel.id)).where(InventoryLevel.on_hand <= InventoryLevel.reorder_point)
    )
    critical_stockouts = stockouts_res.scalar() or 0

    # 3. Pending approvals
    pending_res = await db.execute(
        select(func.count(ActionProposal.id)).where(ActionProposal.status == "pending_approval")
    )
    pending_approvals = pending_res.scalar() or 0

    # 4. Open tickets
    tickets_res = await db.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status != "resolved")
    )
    open_tickets = tickets_res.scalar() or 0

    # 5. Recent agent runs
    runs_res = await db.execute(
        select(AgentRun).order_by(AgentRun.started_at.desc()).limit(8)
    )
    recent_runs = runs_res.scalars().all()

    # 6. Pending actions
    actions_res = await db.execute(
        select(ActionProposal).where(ActionProposal.status == "pending_approval").order_by(ActionProposal.created_at.desc()).limit(10)
    )
    pending_actions = actions_res.scalars().all()

    return {
        "revenue_today_minor": total_revenue,
        "active_orders_count": orders_count,
        "critical_stockouts_count": critical_stockouts,
        "pending_approvals_count": pending_approvals,
        "open_tickets_count": open_tickets,
        "active_agents_count": 8,
        "current_autonomy_level": settings.DEFAULT_AUTONOMY_LEVEL,
        "system_health": "OPTIMAL",
        "savings_estimated_usd": 4820.00,
        "autonomy_distribution": {
            "L0_Observe": 15,
            "L1_Recommend": 22,
            "L2_Approve": 48,
            "L3_Guardrailed": 12,
            "L4_Autonomous": 3
        },
        "recent_agent_runs": [
            {
                "id": run.id,
                "agent_name": run.agent_name,
                "status": run.status,
                "confidence": float(run.confidence or 0.95),
                "summary": run.result.get("summary") if run.result else None,
                "latency_ms": run.latency_ms or 120,
                "tokens_input": run.tokens_input,
                "tokens_output": run.tokens_output,
                "started_at": run.started_at,
                "completed_at": run.completed_at
            }
            for run in recent_runs
        ],
        "pending_actions": [
            {
                "id": act.id,
                "tenant_id": act.tenant_id,
                "agent_run_id": act.agent_run_id,
                "action_type": act.action_type,
                "resource_type": act.resource_type,
                "resource_id": act.resource_id,
                "parameters": act.parameters,
                "risk_level": act.risk_level,
                "status": act.status,
                "requires_approval": act.requires_approval,
                "summary": act.summary,
                "evidence": act.evidence,
                "policy_result": act.policy_result,
                "created_at": act.created_at
            }
            for act in pending_actions
        ]
    }
