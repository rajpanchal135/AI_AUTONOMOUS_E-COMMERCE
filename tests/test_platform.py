import pytest
from brain.inventory.forecast import calculate_inventory_metrics
from brain.shared.policy_engine import PolicyEngine
from brain.shared.contracts import ProposedAction
from brain.supervisor.router import resolve_agents_for_event
from brain.supervisor.langgraph_orchestrator import langgraph_engine
from apps.api.auth import hash_password, verify_password, create_access_token, decode_token

def test_inventory_calculations():
    # SKU RUN-SHOE-BLK-42: on_hand=20, reserved=5, inbound=0, daily_velocity=10.0, lead_time=12
    metrics = calculate_inventory_metrics(
        on_hand=20,
        reserved=5,
        inbound=0,
        daily_velocity=10.0,
        lead_time_days=12,
        target_days_cover=45
    )
    assert metrics["net_available"] == 15
    assert metrics["days_of_cover"] == 1.5
    assert metrics["is_low_stock"] is True
    assert metrics["recommended_reorder_qty"] > 0
    assert metrics["recommended_reorder_qty"] % 10 == 0  # Pack size aligned

def test_auth_password_and_jwt():
    plain = "SuperSecurePassword123!"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

    token = create_access_token({"sub": "user-123", "role": "admin", "tenant_id": "tenant-1"})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"

def test_langgraph_multi_agent_execution():
    initial_state = {
        "tenant_id": "tenant-1",
        "event_type": "inventory.stock_low",
        "correlation_id": "corr-101",
        "autonomy_level": 2,
        "negotiation_turn_count": 0,
        "working_capital_budget_minor": 5000000,  # $50,000 budget pool
        "raw_payload": {
            "sku_code": "RUN-SHOE-BLK-42",
            "on_hand": 10,
            "daily_velocity": 10.0,
            "lead_time_days": 14,
            "cost_minor": 4200,
            "price_minor": 14900
        },
        "inventory_data": {},
        "pricing_data": {},
        "marketing_data": {},
        "orders_data": {},
        "support_data": {},
        "logistics_data": {},
        "risk_data": {},
        "proposals": [],
        "conflict_resolution_notes": [],
        "final_actions_to_execute": [],
        "hitl_required": False,
        "interrupt_reason": None
    }
    result = langgraph_engine.invoke(initial_state)
    assert len(result["final_actions_to_execute"]) >= 2
    action_types = [a["action_type"] for a in result["final_actions_to_execute"]]
    assert "purchase_order.create" in action_types
    assert "campaign.pause" in action_types
    assert result["hitl_required"] is True  # $12,600 PO triggers HITL checkpointer interrupt

def test_policy_engine_enforces_human_approval_for_po():
    action = ProposedAction(
        action_type="purchase_order.create",
        resource_type="sku",
        resource_id="RUN-SHOE-BLK-42",
        parameters={"quantity": 440, "total_minor": 1848000},
        idempotency_key="tenant:sku:po:123",
        requires_approval=True,
        risk_level="medium"
    )
    result = PolicyEngine.evaluate(action=action, tenant_id="tenant-1", autonomy_level=2)
    assert result["decision"] == "PENDING_APPROVAL"
    assert result["requires_approval"] is True

def test_policy_engine_rejects_missing_idempotency():
    action = ProposedAction(
        action_type="purchase_order.create",
        resource_type="sku",
        resource_id="RUN-SHOE-BLK-42",
        parameters={"quantity": 440},
        idempotency_key="",
        requires_approval=True,
        risk_level="medium"
    )
    result = PolicyEngine.evaluate(action=action, tenant_id="tenant-1", autonomy_level=2)
    assert result["decision"] == "REJECTED"

def test_policy_engine_l3_auto_approves_safe_action():
    action = ProposedAction(
        action_type="ticket.tag_update",
        resource_type="ticket",
        resource_id="TCK-401",
        parameters={"tag": "shipping_delay", "amount_minor": 0},
        idempotency_key="tenant:ticket:tag:123",
        requires_approval=False,
        risk_level="low"
    )
    result = PolicyEngine.evaluate(action=action, tenant_id="tenant-1", autonomy_level=3)
    assert result["decision"] == "APPROVED"
    assert result["requires_approval"] is False

def test_supervisor_routes():
    agents = resolve_agents_for_event("inventory.stock_low")
    assert "inventory" in agents
    assert "marketing" in agents
