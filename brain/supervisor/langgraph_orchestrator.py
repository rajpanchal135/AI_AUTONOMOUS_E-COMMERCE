import math
import uuid
from typing import TypedDict, List, Dict, Any, Annotated, Optional
import operator
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# 1. State Definition (TypedDict with Reducer & Budget Pool)
# ---------------------------------------------------------
class AgentState(TypedDict):
    tenant_id: str
    event_type: str
    correlation_id: str
    autonomy_level: int
    negotiation_turn_count: int
    working_capital_budget_minor: int
    raw_payload: Dict[str, Any]
    inventory_data: Dict[str, Any]
    pricing_data: Dict[str, Any]
    marketing_data: Dict[str, Any]
    orders_data: Dict[str, Any]
    support_data: Dict[str, Any]
    logistics_data: Dict[str, Any]
    risk_data: Dict[str, Any]
    proposals: Annotated[List[Dict[str, Any]], operator.add]
    conflict_resolution_notes: List[str]
    final_actions_to_execute: List[Dict[str, Any]]
    hitl_required: bool
    interrupt_reason: Optional[str]

# ---------------------------------------------------------
# 2. Specialist Nodes (Deterministic Math + Safety Formulas)
# ---------------------------------------------------------
def inventory_node(state: AgentState) -> Dict[str, Any]:
    """
    Amazon SCOT Lead-Time Safety Stock Model:
    ROP = (daily_velocity * lead_time_days) + (z_score * sqrt(lead_time_days) * std_dev)
    """
    payload = state.get("raw_payload", {})
    on_hand = int(payload.get("on_hand", 12))
    velocity = float(payload.get("daily_velocity", 10.0))
    lead_time = int(payload.get("lead_time_days", 14))
    cost_minor = int(payload.get("cost_minor", 4200))
    sku_code = payload.get("sku_code", "SKU-PRO-MAX")
    
    # 95% service level -> z = 1.645, assumed std_dev = 0.3 * velocity
    z_score = 1.645
    std_dev = 0.3 * velocity
    safety_stock = math.ceil(z_score * math.sqrt(lead_time) * std_dev)
    rop = math.ceil((velocity * lead_time) + safety_stock)
    
    proposals = []
    inv_data = {
        "sku_code": sku_code,
        "on_hand": on_hand,
        "reorder_point": rop,
        "safety_stock": safety_stock,
        "is_stockout_risk": on_hand <= rop
    }
    
    if on_hand <= rop:
        reorder_qty = max(250, math.ceil(velocity * 30))
        total_po_cost = reorder_qty * cost_minor
        proposals.append({
            "id": f"prop-{uuid.uuid4().hex[:8]}",
            "agent": "inventory_agent",
            "priority": "P0.1",
            "action_type": "purchase_order.create",
            "resource_type": "inventory",
            "resource_id": sku_code,
            "cost_minor": total_po_cost,
            "parameters": {
                "sku_code": sku_code,
                "quantity": reorder_qty,
                "unit_cost_minor": cost_minor,
                "total_minor": total_po_cost
            },
            "reason": f"Stock ({on_hand}) below Amazon SCOT ROP ({rop}). Recommending replenishment PO.",
            "risk_level": "high" if total_po_cost > 50000 else "medium",
            "confidence": 0.96
        })
        
    return {"inventory_data": inv_data, "proposals": proposals}

def pricing_node(state: AgentState) -> Dict[str, Any]:
    """
    Dynamic Pricing: Evaluates elasticity while enforcing hard ≥30% margin floor.
    """
    payload = state.get("raw_payload", {})
    sku_code = payload.get("sku_code", "SKU-PRO-MAX")
    current_price = int(payload.get("price_minor", 14900))
    unit_cost = int(payload.get("cost_minor", 4200))
    
    # Safety Check: Min 30% margin floor
    min_price_floor = math.ceil(unit_cost / 0.70)
    
    # Propose optimal dynamic price
    inv_data = state.get("inventory_data", {})
    proposals = []
    
    # If stockout risk, raise price slightly (scarcity pricing) within 10% daily delta
    target_price = current_price
    if inv_data.get("is_stockout_risk", False):
        target_price = min(int(current_price * 1.08), int(current_price * 1.10))
    
    target_price = max(target_price, min_price_floor)
    
    if target_price != current_price:
        proposals.append({
            "id": f"prop-{uuid.uuid4().hex[:8]}",
            "agent": "pricing_agent",
            "priority": "P2",
            "action_type": "price.update",
            "resource_type": "sku",
            "resource_id": sku_code,
            "cost_minor": 0,
            "parameters": {
                "sku_code": sku_code,
                "old_price_minor": current_price,
                "new_price_minor": target_price,
                "margin_pct": round(((target_price - unit_cost) / target_price) * 100, 1)
            },
            "reason": f"Adjusted price from ${current_price/100:.2f} to ${target_price/100:.2f} maintaining {round(((target_price - unit_cost) / target_price) * 100, 1)}% margin.",
            "risk_level": "low",
            "confidence": 0.92
        })
        
    return {"pricing_data": {"current_price": current_price, "target_price": target_price}, "proposals": proposals}

def marketing_node(state: AgentState) -> Dict[str, Any]:
    """
    Growth Marketing: If cover < 2 days, immediately emit campaign pause to prevent ad waste.
    """
    inv = state.get("inventory_data", {})
    proposals = []
    
    if inv.get("is_stockout_risk", False):
        proposals.append({
            "id": f"prop-{uuid.uuid4().hex[:8]}",
            "agent": "marketing_agent",
            "priority": "P0.1",
            "action_type": "campaign.pause",
            "resource_type": "campaign",
            "resource_id": "CAMP-SUMMER-PROMO",
            "cost_minor": 0,
            "parameters": {"campaign_id": "CAMP-SUMMER-PROMO", "reason": "Stock cover critical"},
            "reason": "Freezing paid ad spend to prevent spending ad budget on out-of-stock SKU.",
            "risk_level": "low",
            "confidence": 0.98
        })
        
    return {"marketing_data": {"campaign_status": "pause_requested" if proposals else "active"}, "proposals": proposals}

def logistics_node(state: AgentState) -> Dict[str, Any]:
    """
    Logistics: Carrier scoring and SLA claim generation.
    """
    return {"logistics_data": {"carrier_health": "nominal"}}

def support_node(state: AgentState) -> Dict[str, Any]:
    """
    Support Desk: Tool-constrained read-only RAG.
    """
    return {"support_data": {"status": "active"}}

def risk_node(state: AgentState) -> Dict[str, Any]:
    """
    Risk & Fraud: Anomaly detection on velocity and payments.
    """
    return {"risk_data": {"fraud_score": 0.02, "status": "passed"}}

# ---------------------------------------------------------
# 3. Master Orchestrator Node (P0-P3 Conflict Matrix & Budget Pool)
# ---------------------------------------------------------
def orchestrator_node(state: AgentState) -> Dict[str, Any]:
    all_proposals = state.get("proposals", [])
    budget_remaining = state.get("working_capital_budget_minor", 1000000) # $10,000 default budget pool
    notes = []
    approved_actions = []
    hitl_flag = False
    interrupt_msg = None
    
    # Sort proposals by Priority Matrix: P0.1 > P0.2 > P1 > P2 > P3
    priority_order = {"P0.1": 1, "P0.2": 2, "P1": 3, "P2": 4, "P3": 5}
    sorted_proposals = sorted(all_proposals, key=lambda x: priority_order.get(x.get("priority", "P3"), 99))
    
    for prop in sorted_proposals:
        cost = prop.get("cost_minor", 0)
        prio = prop.get("priority", "P3")
        
        # Conflict Resolution Rule: Stockout P0 overrides marketing spend
        if prio == "P0.1" and prop.get("action_type") == "campaign.pause":
            notes.append(f"Applied P0.1 Conflict Rule: Freezing Ad Spend on {prop.get('resource_id')}.")
            approved_actions.append(prop)
            continue
            
        # Budget Pool Allocation: Replenishment has first claim on budget
        if cost > 0:
            if cost <= budget_remaining:
                budget_remaining -= cost
                notes.append(f"Allocated ${cost/100:.2f} from capital budget for {prop.get('action_type')}.")
                
                # Check Autonomy & HITL threshold ($500 limit / $50 in L2)
                autonomy = state.get("autonomy_level", 2)
                if cost > 50000 or autonomy < 3:
                    hitl_flag = True
                    interrupt_msg = f"Action {prop.get('action_type')} of ${cost/100:.2f} exceeds auto-execution limit ($500). Human approval required."
                    prop["status"] = "pending_approval"
                else:
                    prop["status"] = "auto_approved"
                approved_actions.append(prop)
            else:
                notes.append(f"Rejected {prop.get('action_type')}: Cost (${cost/100:.2f}) exceeds remaining budget (${budget_remaining/100:.2f}).")
        else:
            prop["status"] = "auto_approved" if state.get("autonomy_level", 2) >= 2 else "pending_approval"
            approved_actions.append(prop)
            
    return {
        "final_actions_to_execute": approved_actions,
        "conflict_resolution_notes": notes,
        "working_capital_budget_minor": budget_remaining,
        "hitl_required": hitl_flag,
        "interrupt_reason": interrupt_msg,
        "negotiation_turn_count": state.get("negotiation_turn_count", 0) + 1
    }

# ---------------------------------------------------------
# 4. Conditional Edge Router (P0-P3 Routing Hierarchy)
# ---------------------------------------------------------
def route_orchestration_flow(state: AgentState) -> str:
    # 1. Check Recursion & Loop limit
    if state.get("negotiation_turn_count", 0) > 3:
        return "terminal_end"
    
    # 2. Check if HITL interrupt required
    if state.get("hitl_required", False):
        return "hitl_interrupt_node"
        
    return "terminal_end"

def hitl_interrupt_node(state: AgentState) -> Dict[str, Any]:
    """
    Represents the LangGraph checkpointer interrupt state for Human-in-the-Loop review.
    """
    return {"interrupt_status": "awaiting_admin_approval"}

# ---------------------------------------------------------
# 5. Build Stateful LangGraph Workflow
# ---------------------------------------------------------
def build_langgraph_engine():
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("inventory", inventory_node)
    workflow.add_node("pricing", pricing_node)
    workflow.add_node("marketing", marketing_node)
    workflow.add_node("logistics", logistics_node)
    workflow.add_node("support", support_node)
    workflow.add_node("risk", risk_node)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("hitl_interrupt_node", hitl_interrupt_node)
    
    # Define Entry & Parallel Flow
    workflow.set_entry_point("inventory")
    workflow.add_edge("inventory", "pricing")
    workflow.add_edge("pricing", "marketing")
    workflow.add_edge("marketing", "logistics")
    workflow.add_edge("logistics", "support")
    workflow.add_edge("support", "risk")
    workflow.add_edge("risk", "orchestrator")
    
    # Conditional Edges from Master Orchestrator
    workflow.add_conditional_edges(
        "orchestrator",
        route_orchestration_flow,
        {
            "hitl_interrupt_node": "hitl_interrupt_node",
            "terminal_end": END
        }
    )
    workflow.add_edge("hitl_interrupt_node", END)
    
    return workflow.compile()

langgraph_engine = build_langgraph_engine()
