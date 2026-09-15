"""
tests/run_edge_cases.py
CLI test runner for all 112 enterprise edge cases.
Executes test cases grouped by agent and outputs a detailed industry-grade report.
"""
import asyncio
import inspect
import sys
import time
from typing import List, Tuple, Callable

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["OFFLINE_MODE"] = "1"

from tests import test_all_112_edge_cases as t

AGENT_GROUPS = [
    (
        "AGENT 1: Inventory Intelligence Agent ('The Stock Guardian')",
        [
            ("EC-INV-01", "Flash Sale + Stockout P0 Override", t.test_ec_inv_01_flash_sale_stockout_p0),
            ("EC-INV-02", "Supplier Lead Time Change Undetected", t.test_ec_inv_02_supplier_lead_time_change),
            ("EC-INV-03", "Negative Stock / Oversell Race Condition Guard", t.test_ec_inv_03_negative_stock_oversell),
            ("EC-INV-04", "Seasonal Demand Spike Multiplier", t.test_ec_inv_04_seasonal_demand_spike),
            ("EC-INV-05", "Supplier MOQ Exceeds Budget / Warehouse Capacity", t.test_ec_inv_05_moq_budget_capacity_constraint),
            ("EC-INV-06", "Multi-Warehouse Inventory Aggregation", t.test_ec_inv_06_multi_warehouse_aggregation),
            ("EC-INV-07", "Inbound PO In Transit Duplicate Prevention", t.test_ec_inv_07_inbound_po_duplicate_prevention),
            ("EC-INV-08", "Dead Stock / Obsolete SKU with No Demand", t.test_ec_inv_08_dead_stock_obsolete),
            ("EC-INV-09", "Expiry Date Constraint (Perishables)", t.test_ec_inv_09_expiry_date_constraint),
            ("EC-INV-10", "Supplier Blocked / Compliance Flag", t.test_ec_inv_10_supplier_blocked_compliance),
            ("EC-INV-11", "API Rate Limit / Gemini Fallback", t.test_ec_inv_11_gemini_quota_deterministic_fallback),
            ("EC-INV-12", "Negative Velocity / Return Surge", t.test_ec_inv_12_negative_velocity_return_surge),
            ("EC-INV-13", "Concurrent DB Write Conflict (Optimistic Locking)", t.test_ec_inv_13_concurrent_write_optimistic_locking),
            ("EC-INV-14", "SKU Split / Parent-Child Velocity Inheritance", t.test_ec_inv_14_sku_split_velocity_inheritance),
            ("EC-INV-15", "Cross-Border Landed Cost / Duty Margin Breach", t.test_ec_inv_15_cross_border_duty_margin_breach),
            ("EC-INV-16", "Zero-Division Guard (New SKU)", t.test_ec_inv_16_zero_division_guard),
        ]
    ),
    (
        "AGENT 2: Dynamic Pricing Agent ('The Profit Maximizer')",
        [
            ("EC-PRC-01", "Margin Erosion Cost Increase", t.test_ec_prc_01_margin_erosion_cost_increase),
            ("EC-PRC-02", "Competitor Price War Defense", t.test_ec_prc_02_price_war_defense),
            ("EC-PRC-03", "Inventory P0 Hold Override", t.test_ec_prc_03_inventory_p0_override),
            ("EC-PRC-04", "Legal MAP Violation Guard", t.test_ec_prc_04_map_violation_guard),
            ("EC-PRC-05", "Bundle Incoherence Guard", t.test_ec_prc_05_bundle_incoherence_guard),
            ("EC-PRC-06", "Checkout Session Price Lock", t.test_ec_prc_06_checkout_lock),
            ("EC-PRC-07", "VIP Segment Price Discrimination Prevention", t.test_ec_prc_07_vip_price_discrimination_prevention),
            ("EC-PRC-08", "Tax-Inclusive vs Exclusive Basis", t.test_ec_prc_08_tax_basis_normalization),
            ("EC-PRC-09", "Multi-Currency FX Drift", t.test_ec_prc_09_fx_drift),
            ("EC-PRC-10", "Flash Sale Expiry Rollback", t.test_ec_prc_10_flash_sale_rollback),
            ("EC-PRC-11", "Zero-Cost / Gift SKU Exclusion", t.test_ec_prc_11_gift_sku_exclusion),
            ("EC-PRC-12", "Algorithmic Price Flapping / Oscillation", t.test_ec_prc_12_price_flapping_lock),
            ("EC-PRC-13", "Maximum Retail Price (MRP) Statutory Ceiling", t.test_ec_prc_13_mrp_statutory_ceiling),
            ("EC-PRC-14", "Scarcity Pricing Runout Slowdown", t.test_ec_prc_14_scarcity_pricing_uplift),
            ("EC-PRC-15", "A/B Experiment Price Freeze", t.test_ec_prc_15_ab_experiment_freeze),
            ("EC-PRC-16", "Stale Competitor Scrape Data Rejection", t.test_ec_prc_16_stale_competitor_data_rejection),
        ]
    ),
    (
        "AGENT 3: Customer Support Agent ('The Issue Solver')",
        [
            ("EC-SUP-01", "Unverified Hallucinated Delivery Date Guard", t.test_ec_sup_01_unverified_delivery_date),
            ("EC-SUP-02", "Serial Refund Fraud Pattern", t.test_ec_sup_02_serial_refund_fraud),
            ("EC-SUP-03", "Angry Customer Sentiment Escalation", t.test_ec_sup_03_angry_sentiment_escalation),
            ("EC-SUP-04", "Multi-Lingual / Regional Language Support", t.test_ec_sup_04_multilingual_support),
            ("EC-SUP-05", "Prompt Injection Attack Defense", t.test_ec_sup_05_prompt_injection_defense),
            ("EC-SUP-06", "Order Not Found / Ambiguous Lookup", t.test_ec_sup_06_order_not_found),
            ("EC-SUP-07", "Legal / Chargeback Threat P0 Escalation", t.test_ec_sup_07_legal_chargeback_threat_p0),
            ("EC-SUP-08", "PII Leak Across Multi-Tenant Boundaries", t.test_ec_sup_08_pii_tenant_isolation),
            ("EC-SUP-09", "Duplicate Ticket / Spam Flood Rate Limit", t.test_ec_sup_09_duplicate_ticket_rate_limit),
            ("EC-SUP-10", "Return Window Expiry Enforcement", t.test_ec_sup_10_return_window_expiry),
            ("EC-SUP-11", "High-Value Refund Approval Gate", t.test_ec_sup_11_high_value_refund_gate),
            ("EC-SUP-12", "Stale Knowledge Base Article Guard", t.test_ec_sup_12_stale_kb_article),
            ("EC-SUP-13", "VIP Customer SLA Breach Warning", t.test_ec_sup_13_vip_sla_breach_warning),
            ("EC-SUP-14", "Payment Card / PAN Redaction", t.test_ec_sup_14_pan_card_redaction),
            ("EC-SUP-15", "Ambiguous Customer Clarification Loop", t.test_ec_sup_15_ambiguous_clarification),
            ("EC-SUP-16", "Prohibited Marketing Language in Support", t.test_ec_sup_16_prohibited_marketing_in_support),
        ]
    ),
    (
        "AGENT 4: Order Management Agent ('The Workflow Master')",
        [
            ("EC-ORD-01", "Payment Gateway Webhook Delay", t.test_ec_ord_01_webhook_reconciliation),
            ("EC-ORD-02", "Unserviceable Pincode / Bad Address", t.test_ec_ord_02_bad_address_hold),
            ("EC-ORD-03", "Inventory Oversell Race Condition (Order Side)", t.test_ec_ord_03_oversell_allocation_race),
            ("EC-ORD-04", "Partial Fulfillment (Split Items)", t.test_ec_ord_04_partial_fulfillment_split),
            ("EC-ORD-05", "COD Fraud High Risk Pincode Hold", t.test_ec_ord_05_cod_fraud_pincode_hold),
            ("EC-ORD-06", "Duplicate Order Placement Guard", t.test_ec_ord_06_duplicate_order_guard),
            ("EC-ORD-07", "B2B GSTIN Invoice Tax Invalidation", t.test_ec_ord_07_b2b_gstin_tax_invalidation),
            ("EC-ORD-08", "Delivery Delayed Tracking Stale Escalation", t.test_ec_ord_08_delayed_tracking_escalation),
            ("EC-ORD-09", "Multi-Currency FX Capture Tolerance", t.test_ec_ord_09_fx_capture_tolerance),
            ("EC-ORD-10", "Hazmat Item Non-Compliant Carrier", t.test_ec_ord_10_hazmat_carrier_compliance),
            ("EC-ORD-11", "Stale Pending Order Cancellation", t.test_ec_ord_11_stale_pending_order_cancellation),
            ("EC-ORD-12", "Same-Day Delivery Cutoff Miss", t.test_ec_ord_12_same_day_cutoff_miss),
            ("EC-ORD-13", "High-Value Return Without Inspection", t.test_ec_ord_13_high_value_return_inspection),
            ("EC-ORD-14", "Cancelled Order Inbound Webhook Handling", t.test_ec_ord_14_cancelled_order_warehouse_webhook),
            ("EC-ORD-15", "Tenant Data Cross-Contamination Guard", t.test_ec_ord_15_tenant_isolation_guard),
            ("EC-ORD-16", "Order Modification During Fulfillment Transition", t.test_ec_ord_16_order_modification_fulfillment_transition),
        ]
    ),
    (
        "AGENT 5: Logistics & Delivery Agent ('The Supply Chain Optimizer')",
        [
            ("EC-LOG-01", "Lost in Transit (72h No Scan) Protocol", t.test_ec_log_01_lost_in_transit),
            ("EC-LOG-02", "Last-Mile Delivery Hub Stagnation", t.test_ec_log_02_hub_stagnation),
            ("EC-LOG-03", "Carrier Weight Discrepancy Flag", t.test_ec_log_03_weight_discrepancy),
            ("EC-LOG-04", "Extreme Weather / Civil Route Disruption", t.test_ec_log_04_weather_disruption),
            ("EC-LOG-05", "Inter-Warehouse Transfer Balancing", t.test_ec_log_05_inter_warehouse_transfer),
            ("EC-LOG-06", "RTO (Return to Origin) Failure Alert", t.test_ec_log_06_rto_alert),
            ("EC-LOG-07", "Hazmat Packaging & Carrier Compliance", t.test_ec_log_07_hazmat_compliance),
            ("EC-LOG-08", "Temperature-Sensitive Cold Chain Violation", t.test_ec_log_08_cold_chain_violation),
            ("EC-LOG-09", "High-Value Shipment Auto-Insurance", t.test_ec_log_09_high_value_insurance),
            ("EC-LOG-10", "Multi-Origin Split-Shipment Optimization", t.test_ec_log_10_split_shipment),
            ("EC-LOG-11", "Green Fleet / Sustainability Routing", t.test_ec_log_11_green_fleet_routing),
            ("EC-LOG-12", "Mid-Transit Carrier Handoff Tracking Loss", t.test_ec_log_12_carrier_handoff_tracking),
            ("EC-LOG-13", "GPS Delivery Fraud / Geofence Breach", t.test_ec_log_13_gps_geofence_fraud),
            ("EC-LOG-14", "Customs Clearance Document Stagnation", t.test_ec_log_14_customs_stagnation),
            ("EC-LOG-15", "Carrier Rate & SLA Composite Scoring", t.test_ec_log_15_carrier_composite_scoring),
            ("EC-LOG-16", "Carbon Footprint Emissions Calculation", t.test_ec_log_16_carbon_footprint_reporting),
        ]
    ),
    (
        "AGENT 6: Marketing Automation Agent ('The Growth Hacker')",
        [
            ("EC-MKT-01", "Out-of-Stock Ad Spend Wastage Guard (P0)", t.test_ec_mkt_01_oos_ad_spend_guard_p0),
            ("EC-MKT-02", "GDPR / Consent Missing Hard Stop", t.test_ec_mkt_02_gdpr_consent_hard_stop),
            ("EC-MKT-03", "RFM Segment Churn Risk Win-Back", t.test_ec_mkt_03_rfm_churn_winback),
            ("EC-MKT-04", "Negative Margin Promotional Campaign Block", t.test_ec_mkt_04_negative_margin_promo_block),
            ("EC-MKT-05", "Brand Safety / Inappropriate Content Shield", t.test_ec_mkt_05_brand_safety_filter),
            ("EC-MKT-06", "High Frequency Message Burnout Prevention", t.test_ec_mkt_06_frequency_burnout_cap),
            ("EC-MKT-07", "Stale Ad Spend Data Reporting Guard", t.test_ec_mkt_07_stale_ads_data_guard),
            ("EC-MKT-08", "Incompatible Multi-Coupon Stacking Block", t.test_ec_mkt_08_multi_coupon_stacking_block),
            ("EC-MKT-09", "Promo Price Mismatch with Live Catalog", t.test_ec_mkt_09_catalog_price_mismatch),
            ("EC-MKT-10", "Abandoned Cart Window Expiry Timing", t.test_ec_mkt_10_abandoned_cart_expiry),
            ("EC-MKT-11", "Underperforming ROAS Auto-Pause", t.test_ec_mkt_11_low_roas_auto_pause),
            ("EC-MKT-12", "Regulatory Discount Claim Restrictions", t.test_ec_mkt_12_regulatory_claims_restriction),
            ("EC-MKT-13", "VIP Audience Protection from Mass Blasts", t.test_ec_mkt_13_vip_exclusion_from_mass_blast),
            ("EC-MKT-14", "Email Template Unreplaced Variable Guard", t.test_ec_mkt_14_unreplaced_template_variable_guard),
            ("EC-MKT-15", "Flash Sale Viral Demand Surge Alert", t.test_ec_mkt_15_viral_demand_surge),
            ("EC-MKT-16", "High Spam Complaint Escalation Threshold", t.test_ec_mkt_16_high_spam_complaint_escalation),
        ]
    ),
    (
        "AGENT 7: Master Orchestrator Agent ('The Hive Brain')",
        [
            ("EC-ORC-01", "Deadlock Timeout Guard (60s Circuit Breaker)", t.test_ec_orc_01_deadlock_timeout),
            ("EC-ORC-02", "Silent Agent Crash / Heartbeat Failure", t.test_ec_orc_02_silent_crash_heartbeat),
            ("EC-ORC-03", "Infinite Event Trigger Loop Breaker", t.test_ec_orc_03_infinite_loop_breaker),
            ("EC-ORC-04", "Approval Queue Overflow Escalation", t.test_ec_orc_04_approval_queue_overflow),
            ("EC-ORC-05", "Natural Language Safety & Financial Limits", t.test_ec_orc_05_nl_command_financial_limits),
            ("EC-ORC-06", "Cross-Tenant Data Isolation Enforcement", t.test_ec_orc_06_cross_tenant_isolation),
            ("EC-ORC-07", "Event Schema Evolution & Backward Compatibility", t.test_ec_orc_07_event_schema_backward_compatibility),
            ("EC-ORC-08", "Prompt Version Drift Detection", t.test_ec_orc_08_prompt_version_drift),
            ("EC-ORC-09", "Priority Inversion Guard (P0 Overrides P3)", t.test_ec_orc_09_priority_inversion_p0_overrides_p3),
            ("EC-ORC-10", "Cascade Storm Throttling (Rate Limiting)", t.test_ec_orc_10_cascade_storm_rate_limiting),
            ("EC-ORC-11", "Partial Agent Run Rollback on Failure", t.test_ec_orc_11_partial_run_rollback),
            ("EC-ORC-12", "Conflicting Direction Proposals on Same Resource", t.test_ec_orc_12_conflicting_proposals_same_resource),
            ("EC-ORC-13", "Multi-Region Event Ordering & Deduplication", t.test_ec_orc_13_multi_region_deduplication),
            ("EC-ORC-14", "Database Connection Pool Starvation Guard", t.test_ec_orc_14_db_pool_starvation_guard),
            ("EC-ORC-15", "Gemini Free-Tier Quota Exhaustion Degradation", t.test_ec_orc_15_gemini_quota_exhaustion_degradation),
            ("EC-ORC-16", "Stale Action Proposal Expiry Auto-Revoke", t.test_ec_orc_16_stale_proposal_expiry_revoke),
        ]
    )
]

def run_test(fn: Callable) -> Tuple[bool, str, float]:
    start = time.perf_counter()
    try:
        if inspect.iscoroutinefunction(fn):
            asyncio.run(fn())
        else:
            fn()
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return True, "OK", elapsed_ms
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        err_msg = str(e) or e.__class__.__name__
        return False, err_msg, elapsed_ms

def main():
    print("=" * 80)
    print("  AI-POWERED AUTONOMOUS E-COMMERCE PLATFORM — ENTERPRISE VERIFICATION SUITE")
    print("  Target: All 7 Agents x 16 Edge Cases = 112 Industry-Grade Tests")
    print("=" * 80)
    print()

    total_passed = 0
    total_failed = 0
    failures = []

    suite_start = time.perf_counter()

    for agent_title, test_cases in AGENT_GROUPS:
        print(f"▶ {agent_title}")
        agent_passed = 0
        agent_failed = 0

        for code, name, fn in test_cases:
            passed, err, elapsed_ms = run_test(fn)
            if passed:
                agent_passed += 1
                total_passed += 1
                print(f"    [PASS] {code}: {name:<50} ({elapsed_ms:5.2f}ms)")
            else:
                agent_failed += 1
                total_failed += 1
                failures.append((code, name, err))
                print(f"    [FAIL] {code}: {name:<50} (ERR: {err})")

        score_pct = (agent_passed / len(test_cases)) * 100
        print(f"  ── Score: {agent_passed}/{len(test_cases)} ({score_pct:.1f}%)\n")

    total_time_ms = (time.perf_counter() - suite_start) * 1000.0
    total_tests = total_passed + total_failed

    print("=" * 80)
    print(f"  VERIFICATION SUMMARY:")
    print(f"  Total Edge Cases Tested: {total_tests}")
    print(f"  Total Passed:            {total_passed}")
    print(f"  Total Failed:            {total_failed}")
    print(f"  Execution Time:          {total_time_ms:.2f}ms")
    print(f"  Final Compliance Score:  {(total_passed / total_tests) * 100:.1f}%")
    print("=" * 80)

    if failures:
        print("\nFAILED EDGE CASES:")
        for code, name, err in failures:
            print(f"  - {code} ({name}): {err}")
        sys.exit(1)
    else:
        print("\n>>> ALL 112 ENTERPRISE EDGE CASES COMPLETED AND VERIFIED SUCCESSFULLY! <<<")
        sys.exit(0)

if __name__ == "__main__":
    main()
