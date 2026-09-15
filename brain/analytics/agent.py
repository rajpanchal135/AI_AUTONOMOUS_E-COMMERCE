"""
brain/analytics/agent.py
Analytics Specialist Agent — "The Intelligence Engine"
Produces daily briefs, anomalies decomposition, cross-domain KPI rollups,
margin dilution alerts, and carbon footprint telemetry.
"""
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from brain.shared.contracts import (
    AgentRunResult, ProposedAction, EvidenceItem,
    RiskLevel, Priority, AutonomyLevel
)
from brain.shared.gemini_client import gemini_client


class AnalyticsAgent:
    """
    Analytics Specialist Agent:
    Produces daily briefs, anomalies decomposition, carbon reporting,
    and cross-domain KPI rollups.
    """
    NAME = "analytics"

    async def generate_daily_brief(
        self,
        tenant_id: str,
        total_revenue_minor: int,
        orders_count: int,
        stockout_skus_count: int,
        pending_approvals: int,
        avg_fulfillment_hours: float = 24.0,
        total_co2_grams: float = 0.0,
    ) -> AgentRunResult:
        run_id = str(uuid.uuid4())
        evidence = [
            EvidenceItem(
                type="sales_aggregate",
                ref="metrics:daily_summary",
                claim=f"Revenue: ${total_revenue_minor/100:,.2f} across {orders_count} orders."
            ),
            EvidenceItem(
                type="inventory_aggregate",
                ref="metrics:stock_health",
                claim=f"{stockout_skus_count} SKUs currently below reorder safety thresholds."
            ),
            EvidenceItem(
                type="fulfillment_aggregate",
                ref="metrics:fulfillment_sla",
                claim=f"Average fulfillment turnaround: {avg_fulfillment_hours:.1f} hours."
            ),
            EvidenceItem(
                type="sustainability_aggregate",
                ref="metrics:carbon_footprint",
                claim=f"Total estimated logistics CO2: {total_co2_grams/1000:.2f} kg."
            )
        ]

        # ── Gemini AI Analytics Synthesis ───────────────────────────────────────
        prompt = (
            f"Generate an Executive Daily Operations Brief for E-Commerce Enterprise:\n"
            f"- Daily Gross Revenue: ${total_revenue_minor/100:,.2f} across {orders_count} orders\n"
            f"- Stockout Risks: {stockout_skus_count} SKUs requiring reorder\n"
            f"- Pending Approvals: {pending_approvals} actions in queue\n"
            f"- Fulfillment Turnaround: {avg_fulfillment_hours:.1f} hours avg\n"
            f"- Logistics CO2: {total_co2_grams/1000:.2f} kg\n"
            f"Provide a 2-sentence executive operational performance summary and strategic recommendation."
        )
        ai_summary = await gemini_client.generate_text(
            prompt=prompt,
            system_prompt="You are the Analytics & Intelligence Agent ('The Intelligence Engine'). Provide strategic, data-driven executive briefings."
        )

        model_id = gemini_client.model if ai_summary else "deterministic_fallback"

        if ai_summary:
            summary = ai_summary.strip()
        else:
            summary = (
                f"Daily Operations Brief: Platform observed ${total_revenue_minor/100:,.2f} in daily transactions. "
                f"{stockout_skus_count} SKU reorder warnings and {pending_approvals} action proposals require review. "
                f"Fulfillment SLA: {avg_fulfillment_hours:.1f}h avg. Logistics CO2: {total_co2_grams/1000:.2f}kg."
            )

        return AgentRunResult(
            run_id=run_id,
            tenant_id=tenant_id,
            agent=self.NAME,
            summary=summary,
            confidence=0.98,
            risk_level=RiskLevel.LOW,
            evidence=evidence,
            proposed_actions=[],
            gemini_prompt=prompt,
            gemini_response=ai_summary or summary,
            metadata={
                "total_revenue_minor": total_revenue_minor,
                "orders_count": orders_count,
                "stockout_skus_count": stockout_skus_count,
                "pending_approvals": pending_approvals,
                "avg_fulfillment_hours": avg_fulfillment_hours,
                "total_co2_grams": total_co2_grams,
                "model_id": model_id,
            }
        )

    async def detect_anomalies(
        self,
        tenant_id: str,
        current_daily_revenue_minor: int,
        expected_daily_revenue_minor: int,
        refund_rate_pct: float,
        expected_refund_rate_pct: float = 2.0,
        margin_pct: float = 35.0,
        min_margin_floor_pct: float = 25.0,
    ) -> AgentRunResult:
        """
        Detects significant operational anomalies:
        - Revenue drops > 20% (L0 alert)
        - Refund rate spikes > 3x normal (L1 recommend fraud audit)
        - Margin compression below floor (L1 alert pricing)
        """
        run_id = str(uuid.uuid4())
        evidence: List[EvidenceItem] = []
        proposed_actions: List[ProposedAction] = []
        anomalies_found: List[str] = []
        risk_level = RiskLevel.LOW

        # Revenue check
        if expected_daily_revenue_minor > 0:
            rev_ratio = current_daily_revenue_minor / expected_daily_revenue_minor
            if rev_ratio < 0.80:
                drop_pct = round((1.0 - rev_ratio) * 100, 1)
                anomalies_found.append(f"Revenue drop of {drop_pct}% vs baseline")
                risk_level = RiskLevel.HIGH
                evidence.append(EvidenceItem(
                    type="revenue_anomaly",
                    ref="analytics:anomaly:revenue_drop",
                    claim=f"Revenue fell {drop_pct}% below expected baseline (${current_daily_revenue_minor/100:,.2f} vs ${expected_daily_revenue_minor/100:,.2f}).",
                    confidence=0.95
                ))

        # Refund spike check
        if refund_rate_pct > (expected_refund_rate_pct * 3.0) and refund_rate_pct > 5.0:
            anomalies_found.append(f"Refund rate spike: {refund_rate_pct:.1f}% vs baseline {expected_refund_rate_pct:.1f}%")
            if risk_level != RiskLevel.CRITICAL:
                risk_level = RiskLevel.HIGH
            evidence.append(EvidenceItem(
                type="refund_anomaly",
                ref="analytics:anomaly:refund_spike",
                claim=f"Refund rate at {refund_rate_pct:.1f}% (>3x baseline {expected_refund_rate_pct:.1f}%). Possible quality or fraud issue.",
                confidence=0.90
            ))
            proposed_actions.append(ProposedAction(
                action_type="audit.fraud_investigation",
                resource_type="analytics",
                resource_id=f"{tenant_id}:refund_spike",
                parameters={"refund_rate_pct": refund_rate_pct, "baseline_pct": expected_refund_rate_pct},
                idempotency_key=f"{tenant_id}:refund_spike:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                requires_approval=True,
                risk_level=RiskLevel.HIGH,
                priority=Priority.P1,
            ))

        # Margin compression check
        if margin_pct < min_margin_floor_pct:
            anomalies_found.append(f"Margin compression: {margin_pct:.1f}% < floor {min_margin_floor_pct:.1f}%")
            risk_level = RiskLevel.HIGH
            evidence.append(EvidenceItem(
                type="margin_compression",
                ref="analytics:anomaly:margin_dilution",
                claim=f"Gross margin of {margin_pct:.1f}% breached policy floor of {min_margin_floor_pct:.1f}%.",
                confidence=0.99
            ))

        summary = (
            f"[Analytics] Anomalies detected: {'; '.join(anomalies_found)}"
            if anomalies_found else
            "[Analytics] All daily performance indicators within expected standard distribution bands."
        )

        return AgentRunResult(
            run_id=run_id,
            tenant_id=tenant_id,
            agent=self.NAME,
            summary=summary,
            confidence=0.95,
            risk_level=risk_level,
            evidence=evidence,
            proposed_actions=proposed_actions,
            metadata={"anomalies_count": len(anomalies_found), "anomalies": anomalies_found}
        )
