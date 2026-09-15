import urllib.request
import urllib.error
import json
import uuid
import sys

BASE_URL = "http://127.0.0.1:8001"

def make_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    req_data = json.dumps(data).encode("utf-8") if data else None
    if req_data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}

def run_e2e_suite():
    print("=========================================================")
    print("🚀 RUNNING PHASE 2 ENTERPRISE END-TO-END VERIFICATION")
    print("=========================================================")

    # 1. Signup Customer
    test_email = f"shopper_{uuid.uuid4().hex[:6]}@example.com"
    print(f"\n[1/8] Testing Customer Signup: {test_email}...")
    status, signup_res = make_request(
        f"{BASE_URL}/api/v1/auth/signup",
        method="POST",
        data={"email": test_email, "password": "SecurePassword123!", "name": "Aarav Mehta", "role": "customer"}
    )
    print("Signup Status:", status)
    assert status == 200, f"Signup failed: {signup_res}"
    cust_token = signup_res["access_token"]
    assert cust_token, "Missing access token"

    # 2. Login as Admin
    print("\n[2/8] Testing Admin Login...")
    status, admin_login_res = make_request(
        f"{BASE_URL}/api/v1/auth/login",
        method="POST",
        data={"email": "admin@autonomous.store", "password": "admin123"}
    )
    print("Admin Login Status:", status)
    assert status == 200, f"Admin login failed: {admin_login_res}"
    admin_token = admin_login_res["access_token"]
    assert admin_login_res["user"]["role"] == "admin"

    # 3. Stock Reservation (15-min TTL & Price Lock)
    print("\n[3/8] Testing 15-Minute Time-Bound Stock Reservation...")
    status, res_data = make_request(
        f"{BASE_URL}/api/v1/inventory/RUN-SHOE-BLK-42/reserve",
        method="POST",
        data={"quantity": 1, "session_id": "sess-test-123"}
    )
    print("Reservation Result:", json.dumps(res_data, indent=2))
    assert status == 200, f"Reservation failed: {res_data}"
    res_id = res_data["reservation_id"]
    assert res_data["expires_in_seconds"] == 900  # 15 minutes

    # 4. Checkout with Idempotency Key & Reservation
    print("\n[4/8] Testing Idempotent Checkout with Stock Reservation...")
    idempotency_key = f"idem-{uuid.uuid4()}"
    checkout_payload = {
        "sku_code": "RUN-SHOE-BLK-42",
        "quantity": 1,
        "customer_name": "Aarav Mehta",
        "customer_email": test_email,
        "shipping_address": "402 Silicon Enclave, Indiranagar, Bengaluru, KA 560038",
        "payment_method": "Credit Card (•••• 4242)",
        "reservation_id": res_id
    }
    status, checkout_res = make_request(
        f"{BASE_URL}/api/v1/orders/checkout",
        method="POST",
        data=checkout_payload,
        headers={"Idempotency-Key": idempotency_key, "Authorization": f"Bearer {cust_token}"}
    )
    print("Checkout Result:", json.dumps(checkout_res, indent=2))
    assert status == 200, f"Checkout failed: {checkout_res}"
    order_id = checkout_res["order_id"]
    ext_id = checkout_res["external_id"]
    tracking_num = checkout_res["tracking_number"]

    # 4b. Test Idempotency: Repeating exact request should return identical response without double charge
    status_dup, checkout_dup = make_request(
        f"{BASE_URL}/api/v1/orders/checkout",
        method="POST",
        data=checkout_payload,
        headers={"Idempotency-Key": idempotency_key, "Authorization": f"Bearer {cust_token}"}
    )
    assert status_dup == 200
    assert checkout_dup["order_id"] == order_id, "Idempotency duplicate key test failed"
    print("✅ Idempotency Double-Click Protection Verified!")

    # 5. Order & Shipment Live Tracking (Case & Whitespace normalized)
    print(f"\n[5/8] Testing Live Order Tracking for tracking #{tracking_num}...")
    status, track_res = make_request(f"{BASE_URL}/api/v1/orders/track/{tracking_num.lower()} ")
    print("Tracking Result:", json.dumps(track_res, indent=2))
    assert status == 200, f"Tracking lookup failed: {track_res}"
    assert track_res["found"] is True

    # 6. Customer Support Grounded RAG Chat
    print("\n[6/8] Testing Grounded AI Support Concierge...")
    status, chat_res = make_request(
        f"{BASE_URL}/api/v1/tickets/chat",
        method="POST",
        data={"message": f"Where is my order {ext_id}?", "order_id": ext_id, "customer_email": test_email}
    )
    print("Chat Assistant Reply:", chat_res.get("reply"))
    assert status == 200, f"Support chat failed: {chat_res}"
    assert tracking_num in chat_res.get("reply", "") or "dispatched" in chat_res.get("reply", "").lower()

    # 7. LangGraph Multi-Agent Cognitive Run
    print("\n[7/8] Testing LangGraph Multi-Agent Orchestrator...")
    from brain.supervisor.langgraph_orchestrator import langgraph_engine
    lang_state = {
        "tenant_id": "tenant-1",
        "event_type": "inventory.stock_low",
        "correlation_id": f"corr-{uuid.uuid4().hex[:8]}",
        "autonomy_level": 2,
        "negotiation_turn_count": 0,
        "working_capital_budget_minor": 5000000,
        "raw_payload": {
            "sku_code": "RUN-SHOE-BLK-42",
            "on_hand": 8,
            "daily_velocity": 12.0,
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
    lang_out = langgraph_engine.invoke(lang_state)
    print("LangGraph Execution Summary:")
    print(f"  - Actions Generated: {len(lang_out['final_actions_to_execute'])}")
    print(f"  - HITL Checkpointer Interrupt Triggered: {lang_out['hitl_required']}")
    print(f"  - Conflict Notes: {lang_out['conflict_resolution_notes']}")
    assert len(lang_out["final_actions_to_execute"]) >= 2

    # 8. HITL Approval & Optimistic Concurrency Protection
    print("\n[8/8] Testing HITL Approvals & Optimistic Locking...")
    status, pending_actions = make_request(
        f"{BASE_URL}/api/v1/actions?status=pending_approval",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if pending_actions:
        target_action = pending_actions[0]
        action_id = target_action["id"]
        print(f"Approving Action [{action_id}]: {target_action['action_type']}...")
        status, app_res = make_request(
            f"{BASE_URL}/api/v1/actions/{action_id}/approve",
            method="POST",
            data={"decided_by": "admin@autonomous.store", "reason": "Approved in E2E validation test"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert status == 200, f"Approval failed: {app_res}"
        print("Approval Succeeded:", app_res.get("message"))

        # Test Optimistic Lock: Attempting to approve again MUST return 409 Conflict
        status_dup, app_dup = make_request(
            f"{BASE_URL}/api/v1/actions/{action_id}/approve",
            method="POST",
            data={"decided_by": "another_admin@autonomous.store", "reason": "Dual admin collision"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert status_dup == 409, f"Expected 409 Conflict on duplicate approval, got {status_dup}"
        print("✅ Optimistic Locking & Race-Condition Guard Verified (HTTP 409 Conflict)!")

    print("\n=========================================================")
    print("🎉 ALL PHASE 2 ENTERPRISE END-TO-END TESTS PASSED 100%!")
    print("=========================================================")

if __name__ == "__main__":
    run_e2e_suite()
