"""
brain/risk/agent.py
Risk & Fraud Specialist Agent — Full Fraud Scoring Engine
Supports all fraud signals referenced in EC-ORD-05, EC-SUP-02, EC-LOG-06,
and cross-agent fraud pattern matching.
"""
import uuid
from typing import Dict, Any, List, Optional
from brain.shared.contracts import (
    AgentRunResult, ProposedAction, EvidenceItem,
    RiskLevel, Priority, AutonomyLevel, CustomerSegment
)
from brain.shared.gemini_client import gemini_client

# ─────────────────────────────────────────────────────────────────────────────
# Fraud Scoring Thresholds
# ─────────────────────────────────────────────────────────────────────────────

# Score ≥ 0.7 → hold order
FRAUD_HOLD_THRESHOLD = 0.70
# Score ≥ 0.85 → auto-reject
FRAUD_REJECT_THRESHOLD = 0.85

# Individual signal weights
SIGNAL_WEIGHTS = {
    "is_new_customer": 0.15,
    "is_cod": 0.15,
    "is_high_value": 0.20,
    "is_high_fraud_pincode": 0.20,
    "high_refund_velocity": 0.25,         # EC-SUP-02
    "payment_avs_mismatch": 0.30,         # EC-ORD-09: Payment mismatch
    "multiple_failed_payments": 0.20,
    "device_anomaly": 0.15,               # Multiple accounts from same device
    "is_velocity_order_flood": 0.25,      # Many orders from same IP in short time
    "is_international_high_risk": 0.20,
    "no_previous_orders": 0.10,
    "basket_anomaly": 0.15,              # Unusual basket composition (all high-value)
}

HIGH_VALUE_THRESHOLD_MINOR = 150000      # $1,500
COD_HIGH_VALUE_THRESHOLD = 30000         # $300 COD


class RiskAgent:
    """
    Risk & Fraud Specialist Agent

    Computes a composite fraud score (0.0-1.0) using weighted signals.
    Returns typed ProposedActions for hold, review, or rejection.
    Cross-references with Support Agent's refund velocity data.
    """
    NAME = "risk"

    async def evaluate_order_risk(
        self,
        tenant_id: str,
        order_id: str,
        external_id: str,
        total_minor: int,
        payment_status: str,
        customer_id: str,
        # Extended fraud signals
        payment_method: str = "prepaid",
        customer_segment: str = CustomerSegment.NEW,
        customer_refund_count_30d: int = 0,
        customer_order_count: int = 0,
        is_high_fraud_pincode: bool = False,
        destination_country: str = "IN",
        payment_avs_mismatch: bool = False,
        multiple_failed_payments: int = 0,
        device_id: Optional[str] = None,
        device_order_count_1h: int = 0,       # Orders from same device in 1h
        ip_order_count_1h: int = 0,           # Orders from same IP in 1h
        all_items_high_value: bool = False,    # Basket anomaly
        is_international: bool = False,
        high_risk_countries: Optional[List[str]] = None,
    ) -> AgentRunResult:
        run_id = str(uuid.uuid4())
        evidence: List[EvidenceItem] = []
        proposed_actions: List[ProposedAction] = []
        metadata: Dict[str, Any] = {}
        high_risk_countries = high_risk_countries or ["NG", "GH", "PK", "IQ", "BY"]

        # ── Compute Fraud Score ────────────────────────────────────────────────
        score = 0.0
        signals_triggered: List[str] = []

        is_new_customer = customer_segment == CustomerSegment.NEW or customer_order_count == 0
        is_cod = payment_method == "cod"
        is_high_value = total_minor > HIGH_VALUE_THRESHOLD_MINOR
        is_international_high_risk = is_international and destination_country in high_risk_countries

        if is_new_customer:
            score += SIGNAL_WEIGHTS["is_new_customer"]
            signals_triggered.append(f"new_customer (+{SIGNAL_WEIGHTS['is_new_customer']})")

        if is_cod:
            score += SIGNAL_WEIGHTS["is_cod"]
            signals_triggered.append(f"cod_payment (+{SIGNAL_WEIGHTS['is_cod']})")

        if is_high_value:
            score += SIGNAL_WEIGHTS["is_high_value"]
            signals_triggered.append(f"high_value_${total_minor/100:.0f} (+{SIGNAL_WEIGHTS['is_high_value']})")

        if is_high_fraud_pincode:
            score += SIGNAL_WEIGHTS["is_high_fraud_pincode"]
            signals_triggered.append(f"high_fraud_pincode (+{SIGNAL_WEIGHTS['is_high_fraud_pincode']})")

        # EC-SUP-02: High refund velocity cross-reference
        if customer_refund_count_30d > 5:
            score += SIGNAL_WEIGHTS["high_refund_velocity"]
            signals_triggered.append(f"refund_velocity_{customer_refund_count_30d}_in_30d (+{SIGNAL_WEIGHTS['high_refund_velocity']})")

        # EC-ORD-09: Payment mismatch
        if payment_avs_mismatch:
            score += SIGNAL_WEIGHTS["payment_avs_mismatch"]
            signals_triggered.append(f"payment_avs_mismatch (+{SIGNAL_WEIGHTS['payment_avs_mismatch']})")

        if multiple_failed_payments > 2:
            score += SIGNAL_WEIGHTS["multiple_failed_payments"]
            signals_triggered.append(f"failed_payments_{multiple_failed_payments} (+{SIGNAL_WEIGHTS['multiple_failed_payments']})")

        # Device anomaly: multiple accounts from same device
        if device_order_count_1h > 3:
            score += SIGNAL_WEIGHTS["device_anomaly"]
            signals_triggered.append(f"device_anomaly_{device_order_count_1h}_orders_1h (+{SIGNAL_WEIGHTS['device_anomaly']})")

        # IP velocity: order flood
        if ip_order_count_1h > 5:
            score += SIGNAL_WEIGHTS["is_velocity_order_flood"]
            signals_triggered.append(f"ip_flood_{ip_order_count_1h}_orders_1h (+{SIGNAL_WEIGHTS['is_velocity_order_flood']})")

        if is_international_high_risk:
            score += SIGNAL_WEIGHTS["is_international_high_risk"]
            signals_triggered.append(f"international_high_risk_{destination_country} (+{SIGNAL_WEIGHTS['is_international_high_risk']})")

        if customer_order_count == 0:
            score += SIGNAL_WEIGHTS["no_previous_orders"]
            signals_triggered.append(f"no_order_history (+{SIGNAL_WEIGHTS['no_previous_orders']})")

        if all_items_high_value and total_minor > 50000:
            score += SIGNAL_WEIGHTS["basket_anomaly"]
            signals_triggered.append(f"basket_anomaly_all_high_value (+{SIGNAL_WEIGHTS['basket_anomaly']})")

        # Clamp score to [0, 1]
        score = min(1.0, round(score, 3))
        metadata["fraud_score"] = score
        metadata["signals_triggered"] = signals_triggered
        metadata["signals_count"] = len(signals_triggered)

        evidence.append(EvidenceItem(
            type="fraud_score",
            ref=f"order:{order_id}:risk",
            claim=f"Fraud score: {score:.3f} | Signals: {', '.join(signals_triggered) or 'none'} | "
                  f"Order value: ${total_minor/100:.2f} | Payment: {payment_method} | "
                  f"Customer orders (all-time): {customer_order_count}",
            confidence=0.92
        ))

        evidence.append(EvidenceItem(
            type="payment_risk",
            ref=f"order:{order_id}:payment",
            claim=f"Payment status: {payment_status} | AVS mismatch: {payment_avs_mismatch} | "
                  f"Failed attempts: {multiple_failed_payments} | "
                  f"Refunds in 30d: {customer_refund_count_30d}",
            confidence=0.95
        ))

        # ── Decision Based on Score ────────────────────────────────────────────
        if score >= FRAUD_REJECT_THRESHOLD:
            evidence.append(EvidenceItem(
                type="fraud_decision",
                ref=f"order:{order_id}:fraud_reject",
                claim=f"FRAUD REJECT: Score {score:.3f} ≥ reject threshold {FRAUD_REJECT_THRESHOLD}. "
                      f"Order auto-rejected. Customer account flagged for manual review.",
                confidence=0.92
            ))
            proposed_actions.append(ProposedAction(
                action_type="order.cancel",
                resource_type="order", resource_id=external_id,
                parameters={
                    "order_id": order_id, "reason": "fraud_high_confidence",
                    "fraud_score": score, "signals": signals_triggered,
                    "auto_refund": True,
                },
                idempotency_key=f"{tenant_id}:{order_id}:fraud_cancel",
                requires_approval=True, risk_level=RiskLevel.CRITICAL,
                priority=Priority.P0, autonomy_level=AutonomyLevel.L2,
            ))
            summary = (
                f"ORDER #{external_id}: FRAUD REJECT (score={score:.3f} ≥ {FRAUD_REJECT_THRESHOLD}). "
                f"Signals: {len(signals_triggered)}. Auto-cancel proposed. Human review required."
            )
            risk_level = RiskLevel.CRITICAL

        elif score >= FRAUD_HOLD_THRESHOLD:
            evidence.append(EvidenceItem(
                type="fraud_decision",
                ref=f"order:{order_id}:fraud_hold",
                claim=f"FRAUD HOLD: Score {score:.3f} ≥ hold threshold {FRAUD_HOLD_THRESHOLD}. "
                      f"Order held for manual review. No auto-fulfilment.",
                confidence=0.88
            ))
            proposed_actions.append(ProposedAction(
                action_type="order.fraud_hold",
                resource_type="order", resource_id=external_id,
                parameters={
                    "order_id": order_id, "reason": "fraud_medium_confidence",
                    "fraud_score": score, "signals": signals_triggered,
                },
                idempotency_key=f"{tenant_id}:{order_id}:fraud_hold",
                requires_approval=True, risk_level=RiskLevel.HIGH,
                priority=Priority.P1, autonomy_level=AutonomyLevel.L2,
            ))
            summary = (
                f"ORDER #{external_id}: FRAUD HOLD (score={score:.3f}, "
                f"threshold={FRAUD_HOLD_THRESHOLD}). "
                f"Signals: {len(signals_triggered)}. Human verification required."
            )
            risk_level = RiskLevel.HIGH

        else:
            # COD high-value auto-flag even at lower scores (EC-ORD-05)
            if is_cod and total_minor > COD_HIGH_VALUE_THRESHOLD and is_new_customer:
                proposed_actions.append(ProposedAction(
                    action_type="order.fraud_review",
                    resource_type="order", resource_id=external_id,
                    parameters={
                        "order_id": order_id, "reason": "cod_high_value_new_customer",
                        "fraud_score": score,
                    },
                    idempotency_key=f"{tenant_id}:{order_id}:cod_review",
                    requires_approval=True, risk_level=RiskLevel.MEDIUM,
                    priority=Priority.P1, autonomy_level=AutonomyLevel.L2,
                ))
                summary = (
                    f"ORDER #{external_id}: COD HIGH-VALUE REVIEW requested "
                    f"(score={score:.3f}, COD + new customer + ${total_minor/100:.0f}). "
                    f"Fraud risk low but COD pattern warrants verification."
                )
                risk_level = RiskLevel.MEDIUM
            else:
                summary = (
                    f"ORDER #{external_id}: CLEAN (fraud score={score:.3f}, "
                    f"threshold={FRAUD_HOLD_THRESHOLD}). "
                    f"No fraud signals triggered. Proceeding to fulfilment."
                )
                risk_level = RiskLevel.LOW

        # ── Gemini AI Risk Analysis ─────────────────────────────────────────────
        prompt = (
            f"Evaluate Fraud Risk for Order #{external_id}:\n"
            f"- Order Total: ${total_minor/100:.2f}, Payment Method: {payment_method}, Status: {payment_status}\n"
            f"- Customer Segment: {customer_segment}, Refund History (30d): {customer_refund_count_30d}\n"
            f"- Calculated Fraud Risk Score: {score:.2f} (Threshold: {FRAUD_HOLD_THRESHOLD})\n"
            f"- Triggered Risk Signals: {signals_triggered}\n"
            f"Provide a 1-sentence risk verdict and security recommendation."
        )
        ai_summary = await gemini_client.generate_text(
            prompt=prompt,
            system_prompt="You are the Risk & Fraud Specialist Agent. Provide strict, analytical security assessments."
        )

        model_id = gemini_client.model if ai_summary else "deterministic_fallback"

        if ai_summary:
            summary = f"{ai_summary.strip()} | Fraud Score: {score:.2f}."

        return AgentRunResult(
            run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
            summary=summary, confidence=0.92 if score > 0.5 else 0.97,
            risk_level=risk_level,
            evidence=evidence, proposed_actions=proposed_actions,
            metadata={
                **metadata,
                "model_id": model_id,
                "gemini_prompt": prompt,
                "gemini_response": ai_summary or summary,
            },
            gemini_prompt=prompt,
            gemini_response=ai_summary or summary,
            model_id=model_id,
        )
