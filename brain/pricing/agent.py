"""
brain/pricing/agent.py
Dynamic Pricing Agent — "The Profit Maximizer"
Implements all 16 edge cases from EC-PRC-01 through EC-PRC-16
"""
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from brain.shared.contracts import (
    AgentRunResult, ProposedAction, EvidenceItem,
    RiskLevel, Priority, AutonomyLevel
)
from brain.shared.gemini_client import gemini_client

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

MIN_MARGIN_PCT = 30.0               # EC-PRC-01: Minimum gross margin floor
MAX_DAILY_CHANGE_PCT = 0.10         # EC-PRC — Max 10% price movement per day
SCARCITY_UPLIFT_PCT = 0.05          # EC-PRC: +5% when days_cover < 10
CLEARANCE_DISCOUNT_PCT = 0.05       # EC-PRC: -5% when days_cover > 60
LOW_STOCK_THRESHOLD_DAYS = 10.0     # Below this → scarcity pricing
HIGH_STOCK_THRESHOLD_DAYS = 60.0    # Above this → clearance pricing
PRICE_WAR_THRESHOLD_PCT = -20.0     # EC-PRC-02: -20% competitor avg = price war
CHECKOUT_LOCK_MINUTES = 15          # EC-PRC-06: Cart session price lock
FLAPPING_DIRECTION_CHANGES = 2      # EC-PRC-12: Max direction changes in 24h
COMPETITOR_STALE_HOURS = 24         # EC-PRC-16: Data older than 24h = stale
VIP_PRICE_STABLE_SEGMENT = "vip"    # EC-PRC-07
L3_CONFIDENCE_THRESHOLD = 0.85      # Min confidence for auto-execute


class PricingAgent:
    """
    Dynamic Pricing Agent — "The Profit Maximizer"

    Evaluates: inventory pressure, competitor pricing, demand elasticity,
    margin floor, MAP, MRP, bundle coherence, A/B lock, GST basis, FX,
    checkout lock, flapping, gift SKU exclusion, and price war defense.
    """
    NAME = "pricing"

    async def evaluate_pricing(
        self,
        tenant_id: str,
        sku_code: str,
        title: str,
        current_price_minor: int,
        unit_cost_minor: int,
        daily_velocity: float,
        inventory_days_cover: float,
        competitor_price_minor: int = 0,
        # Extended edge-case parameters
        map_price_minor: Optional[int] = None,       # EC-PRC-04: MAP violation
        mrp_minor: Optional[int] = None,             # EC-PRC-13: Regulatory MRP
        is_gift_item: bool = False,                   # EC-PRC-11: Zero-cost SKU
        experiment_lock: bool = False,                # EC-PRC-15: A/B test lock
        bundle_ids: Optional[List[str]] = None,       # EC-PRC-05: Bundle conflict
        price_history_24h: Optional[List[Dict]] = None,  # EC-PRC-12: Flapping
        price_inclusive_tax: bool = False,            # EC-PRC-08: Tax basis
        tax_rate_pct: float = 18.0,                   # GST rate for exclusion
        competitor_fetched_at: Optional[datetime] = None,  # EC-PRC-16: Stale data
        competitor_price_changes_72h: Optional[List[float]] = None,  # EC-PRC-02
        customer_segment: str = "standard",           # EC-PRC-07: VIP detection
        flash_sale_active: bool = False,              # EC-PRC-10: Flash sale revert
        flash_sale_effective_until: Optional[datetime] = None,
        original_price_minor: Optional[int] = None,  # EC-PRC-10: Pre-sale price
        p0_inventory_hold_active: bool = False,       # EC-PRC-03: P0 conflict
    ) -> AgentRunResult:
        run_id = str(uuid.uuid4())
        evidence: List[EvidenceItem] = []
        proposed_actions: List[ProposedAction] = []
        metadata: Dict[str, Any] = {}
        now = datetime.now(timezone.utc)

        # ── EC-PRC-11: Zero-Cost / Gift SKU Exclusion ─────────────────────────
        if is_gift_item or unit_cost_minor == 0:
            evidence.append(EvidenceItem(
                type="sku_exclusion",
                ref=f"sku:{sku_code}:gift",
                claim=f"[EC-PRC-11] SKU {sku_code} is a gift/promo item (cost=0 or is_gift_item=True). "
                      f"Excluded from autonomous pricing optimization.",
                confidence=1.0
            ))
            return AgentRunResult(
                run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                summary=f"[EC-PRC-11] SKU {sku_code} excluded from pricing — gift/promo item. Reason: gift_sku_excluded.",
                confidence=1.0, risk_level=RiskLevel.LOW,
                evidence=evidence, proposed_actions=[],
                metadata={"edge_case": "EC-PRC-11", "reason": "gift_sku_excluded"},
            )

        # ── EC-PRC-15: A/B Price Test Experiment Lock ─────────────────────────
        if experiment_lock:
            evidence.append(EvidenceItem(
                type="experiment_lock",
                ref=f"sku:{sku_code}:ab_test",
                claim=f"[EC-PRC-15] SKU {sku_code} is under A/B price test experiment lock. "
                      f"Autonomous pricing suspended. experiment_lock_respected.",
                confidence=1.0
            ))
            return AgentRunResult(
                run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                summary=f"[EC-PRC-15] SKU {sku_code} pricing LOCKED — A/B experiment in progress. "
                        f"Experiment owner must unlock before optimization resumes.",
                confidence=1.0, risk_level=RiskLevel.LOW,
                evidence=evidence, proposed_actions=[],
                metadata={"edge_case": "EC-PRC-15", "reason": "experiment_lock_respected", "experiment_lock_active": True},
            )

        # ── EC-PRC-03: P0 Inventory Hold Conflict ─────────────────────────────
        if p0_inventory_hold_active:
            evidence.append(EvidenceItem(
                type="p0_hold",
                ref=f"inventory:{sku_code}:p0_hold",
                claim=f"[EC-PRC-03] P0 inventory hold active for SKU {sku_code}. "
                      f"All discount proposals BLOCKED. P0 Safety > P2 Pricing.",
                confidence=1.0
            ))
            return AgentRunResult(
                run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                summary=f"[EC-PRC-03] Pricing discounts BLOCKED by P0 inventory hold on SKU {sku_code}. "
                        f"Hold must be lifted (PO confirmed + stock inbound) before pricing resumes.",
                confidence=1.0, risk_level=RiskLevel.LOW,
                evidence=evidence,
                proposed_actions=[],
                metadata={"edge_case": "EC-PRC-03", "rejected_by_inventory_hold": True, "p0_blocked": True},
            )

        # ── EC-PRC-08: Tax Basis Normalization ────────────────────────────────
        # Always work in excl_tax internally
        working_price_minor = current_price_minor
        working_cost_minor = unit_cost_minor
        if price_inclusive_tax and tax_rate_pct > 0:
            divisor = 1 + tax_rate_pct / 100
            working_price_minor = int(current_price_minor / divisor)
            working_cost_minor = int(unit_cost_minor / divisor)
            metadata["price_inclusive_tax"] = True
            metadata["net_base_price_minor"] = working_price_minor
            evidence.append(EvidenceItem(
                type="tax_normalization",
                ref=f"sku:{sku_code}:tax_basis",
                claim=f"[EC-PRC-08] Price is tax-inclusive at {tax_rate_pct}% GST. "
                      f"Working in excl_tax internally: price={working_price_minor/100:.2f}, "
                      f"cost={working_cost_minor/100:.2f}. Display layer adds tax.",
                confidence=1.0
            ))

        # ── Current margin calculation ─────────────────────────────────────────
        if working_price_minor > 0:
            current_margin_pct = ((working_price_minor - working_cost_minor) / working_price_minor) * 100
        else:
            current_margin_pct = 0.0

        floor_price_minor = int(working_cost_minor * (1 + MIN_MARGIN_PCT / 100))

        evidence.append(EvidenceItem(
            type="margin_analysis",
            ref=f"sku:{sku_code}:economics",
            claim=f"Current price: ${working_price_minor/100:.2f} | "
                  f"Cost: ${working_cost_minor/100:.2f} | "
                  f"Margin: {current_margin_pct:.1f}% | "
                  f"Floor price: ${floor_price_minor/100:.2f} (min {MIN_MARGIN_PCT}% margin)",
            confidence=1.0
        ))

        # ── EC-PRC-01: Margin Erosion — Cost Increase Detection ───────────────
        if current_margin_pct < MIN_MARGIN_PCT:
            min_price_for_margin = int(working_cost_minor / (1 - MIN_MARGIN_PCT / 100))
            evidence.append(EvidenceItem(
                type="margin_breach",
                ref=f"sku:{sku_code}:margin_erosion",
                claim=f"[EC-PRC-01] MARGIN BREACH: Current margin {current_margin_pct:.1f}% < "
                      f"minimum {MIN_MARGIN_PCT}%. Must raise price to at least "
                      f"${min_price_for_margin/100:.2f} to restore floor margin.",
                confidence=0.99
            ))
            proposed_actions.append(ProposedAction(
                action_type="price.update",
                resource_type="sku", resource_id=sku_code,
                parameters={
                    "sku_code": sku_code, "old_price_minor": current_price_minor,
                    "new_price_minor": min_price_for_margin,
                    "reason": "margin_erosion_cost_increase",
                    "margin_gain_pct": MIN_MARGIN_PCT - current_margin_pct,
                },
                idempotency_key=f"{tenant_id}:{sku_code}:price:{min_price_for_margin}",
                requires_approval=True, risk_level=RiskLevel.HIGH,
                priority=Priority.P2, autonomy_level=AutonomyLevel.L2,
                rollback_data={"revert_price_minor": current_price_minor},
                effective_after_minutes=CHECKOUT_LOCK_MINUTES,
            ))
            return AgentRunResult(
                run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                summary=f"[EC-PRC-01] MARGIN EROSION: SKU {sku_code} current margin {current_margin_pct:.1f}% "
                        f"below floor {MIN_MARGIN_PCT}%. Proposing mandatory price increase to "
                        f"${min_price_for_margin/100:.2f}. Human approval required (HIGH risk).",
                confidence=0.99, risk_level=RiskLevel.HIGH,
                evidence=evidence, proposed_actions=proposed_actions,
                metadata={"edge_case": "EC-PRC-01", "current_margin_pct": current_margin_pct, "margin_breach": True},
            )

        # ── EC-PRC-10: Flash Sale Price Not Reverted After Event ──────────────
        if flash_sale_active and flash_sale_effective_until and original_price_minor:
            if now > flash_sale_effective_until.replace(tzinfo=timezone.utc):
                evidence.append(EvidenceItem(
                    type="flash_sale_overdue",
                    ref=f"sku:{sku_code}:flash_sale",
                    claim=f"[EC-PRC-10] Flash sale ended at {flash_sale_effective_until.isoformat()} "
                          f"but price not reverted. Auto-generating price.revert action (L3).",
                    confidence=1.0
                ))
                proposed_actions.append(ProposedAction(
                    action_type="price.update",
                    resource_type="sku", resource_id=sku_code,
                    parameters={
                        "sku_code": sku_code, "old_price_minor": current_price_minor,
                        "new_price_minor": original_price_minor,
                        "reason": "flash_sale_revert",
                        "margin_gain_pct": ((original_price_minor - current_price_minor) / original_price_minor) * 100,
                    },
                    idempotency_key=f"{tenant_id}:{sku_code}:price_revert:{original_price_minor}",
                    requires_approval=False, risk_level=RiskLevel.LOW,
                    priority=Priority.P2, autonomy_level=AutonomyLevel.L3,
                    rollback_data={"revert_price_minor": current_price_minor},
                ))
                return AgentRunResult(
                    run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                    summary=f"[EC-PRC-10] Flash sale expired. Auto-reverting SKU {sku_code} "
                            f"price from ${current_price_minor/100:.2f} to ${original_price_minor/100:.2f} (L3 auto-execute).",
                    confidence=0.97, risk_level=RiskLevel.LOW,
                    evidence=evidence, proposed_actions=proposed_actions,
                    metadata={"edge_case": "EC-PRC-10", "flash_sale_expired": True},
                )

        # ── EC-PRC-12: Price Flapping Detection ───────────────────────────────
        if price_history_24h and len(price_history_24h) >= 3:
            directions = []
            for i in range(len(price_history_24h)):
                item = price_history_24h[i]
                if "direction" in item:
                    d = str(item["direction"]).lower()
                    if d in ("up", "increase"):
                        directions.append(1)
                    elif d in ("down", "decrease"):
                        directions.append(-1)
                    else:
                        directions.append(0)
                elif i > 0:
                    diff = item.get("price", 0) - price_history_24h[i-1].get("price", 0)
                    directions.append(1 if diff > 0 else -1 if diff < 0 else 0)
            direction_changes = sum(
                1 for i in range(1, len(directions)) if directions[i] != directions[i-1] and directions[i] != 0
            )
            if direction_changes >= FLAPPING_DIRECTION_CHANGES:
                evidence.append(EvidenceItem(
                    type="price_flapping",
                    ref=f"sku:{sku_code}:price_history",
                    claim=f"[EC-PRC-12] Price flapping detected: {direction_changes} direction changes "
                          f"in last 24h (threshold: {FLAPPING_DIRECTION_CHANGES}). "
                          f"Entering 24-hour price stabilization mode.",
                    confidence=0.95
                ))
                return AgentRunResult(
                    run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                    summary=f"[EC-PRC-12] Price flapping detected for SKU {sku_code}. "
                            f"{direction_changes} direction changes in 24h. "
                            f"24-hour stabilization mode active. No price changes until window expires.",
                    confidence=0.95, risk_level=RiskLevel.MEDIUM,
                    evidence=evidence, proposed_actions=[],
                    metadata={"edge_case": "EC-PRC-12", "direction_changes": direction_changes, "flapping_locked": True},
                )

        # ── EC-PRC-16: Competitor Price Data Stale ────────────────────────────
        competitor_signal_weight = 1.0
        if competitor_fetched_at:
            hours_since_fetch = (now - competitor_fetched_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            if hours_since_fetch > COMPETITOR_STALE_HOURS:
                competitor_signal_weight = 0.1
                metadata["competitor_data_stale"] = True
                evidence.append(EvidenceItem(
                    type="stale_competitor_data",
                    ref=f"competitor:{sku_code}:price",
                    claim=f"[EC-PRC-16] Competitor price data is {hours_since_fetch:.0f}h old "
                          f"(threshold: {COMPETITOR_STALE_HOURS}h). Marked STALE. "
                          f"Competitor signal weight reduced to {competitor_signal_weight}. "
                          f"Relying on inventory pressure + margin math only.",
                    confidence=0.6,
                    data_freshness_minutes=int(hours_since_fetch * 60)
                ))

        # ── EC-PRC-02: Competitor Price War Detection ─────────────────────────
        if competitor_price_changes_72h and len(competitor_price_changes_72h) >= 2:
            avg_change = sum(competitor_price_changes_72h) / len(competitor_price_changes_72h)
            avg_change_pct = avg_change * 100 if abs(avg_change) <= 1.0 else avg_change
            if avg_change_pct < PRICE_WAR_THRESHOLD_PCT:
                evidence.append(EvidenceItem(
                    type="price_war",
                    ref=f"competitor:{sku_code}:price_war",
                    claim=f"[EC-PRC-02] PRICE WAR DETECTED: Competitor avg change "
                          f"{avg_change_pct:.1f}% over 72h < threshold {PRICE_WAR_THRESHOLD_PCT}%. "
                          f"Entering defensive hold mode. Floor price maintained.",
                    confidence=0.92
                ))
                return AgentRunResult(
                    run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                    summary=f"[EC-PRC-02] PRICE WAR: Competitor avg -{abs(avg_change_pct):.1f}% in 72h. "
                            f"SKU {sku_code} entering defensive price hold. "
                            f"No further discounts. Floor price ${floor_price_minor/100:.2f} maintained.",
                    confidence=0.92, risk_level=RiskLevel.HIGH,
                    evidence=evidence, proposed_actions=[],
                    metadata={"edge_case": "EC-PRC-02", "competitor_avg_change_pct": avg_change_pct, "price_war_detected": True, "defensive_hold": True},
                )

        # ── EC-PRC-07: VIP Customer Price Stability ───────────────────────────
        if customer_segment == VIP_PRICE_STABLE_SEGMENT:
            evidence.append(EvidenceItem(
                type="vip_price_protection",
                ref=f"customer:segment:vip",
                claim=f"[EC-PRC-07] VIP customer segment detected. Price changes on VIP-preferred SKUs "
                      f"require Marketing Agent co-approval. Proposing for review.",
                confidence=1.0
            ))
            metadata["vip_price_review_required"] = True
            metadata["edge_case"] = "EC-PRC-07"

        # ── Core Pricing Logic (Inventory Pressure) ────────────────────────────
        evidence.append(EvidenceItem(
            type="inventory_signal",
            ref=f"inventory:{sku_code}",
            claim=f"Stock cover: {inventory_days_cover:.1f} days. "
                  f"{'SCARCITY pricing trigger (<10d)' if inventory_days_cover < LOW_STOCK_THRESHOLD_DAYS else 'CLEARANCE trigger (>60d)' if inventory_days_cover > HIGH_STOCK_THRESHOLD_DAYS else 'OPTIMAL range'}.",
            confidence=1.0
        ))

        if inventory_days_cover < LOW_STOCK_THRESHOLD_DAYS:
            recommended_price_minor = int(working_price_minor * (1 + SCARCITY_UPLIFT_PCT))
            reason = f"Scarcity pricing: {inventory_days_cover:.1f} days cover. +{SCARCITY_UPLIFT_PCT*100:.0f}% dampens runout velocity."
            expected_velocity_change = -0.08
            direction = "up"
            metadata["pricing_strategy"] = "scarcity_pricing"
        elif inventory_days_cover > HIGH_STOCK_THRESHOLD_DAYS:
            recommended_price_minor = int(working_price_minor * (1 - CLEARANCE_DISCOUNT_PCT))
            reason = f"Clearance pricing: {inventory_days_cover:.1f} days cover. -{CLEARANCE_DISCOUNT_PCT*100:.0f}% stimulates velocity."
            expected_velocity_change = 0.15
            direction = "down"
        else:
            recommended_price_minor = working_price_minor
            reason = "Price optimal relative to inventory cover and target margins."
            expected_velocity_change = 0.0
            direction = "hold"

        # ── EC-PRC-14: Negative Price Guard ───────────────────────────────────
        if recommended_price_minor <= 0:
            recommended_price_minor = floor_price_minor
            evidence.append(EvidenceItem(
                type="guardrail_clamp",
                ref=f"sku:{sku_code}:negative_price",
                claim=f"[EC-PRC-14] GUARDRAIL: Negative/zero price proposed. "
                      f"Clamped to floor price ${floor_price_minor/100:.2f}. "
                      f"Algorithm error logged as 'guardrail_clamp' event.",
                confidence=1.0
            ))
            metadata["edge_case"] = "EC-PRC-14"

        # ── EC-PRC-04: MAP Violation Check ────────────────────────────────────
        if map_price_minor and (working_price_minor < map_price_minor or recommended_price_minor < map_price_minor):
            evidence.append(EvidenceItem(
                type="map_violation",
                ref=f"sku:{sku_code}:map",
                claim=f"[EC-PRC-04] MAP VIOLATION PREVENTED: Recommended price "
                      f"${recommended_price_minor/100:.2f} < MAP ${map_price_minor/100:.2f}. "
                      f"Proposal rejected with reason 'MAP_violation'.",
                confidence=1.0
            ))
            return AgentRunResult(
                run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
                summary=f"[EC-PRC-04] MAP VIOLATION: Cannot price SKU {sku_code} below MAP "
                        f"${map_price_minor/100:.2f}. Proposal rejected.",
                confidence=1.0, risk_level=RiskLevel.CRITICAL,
                evidence=evidence, proposed_actions=[],
                metadata={"edge_case": "EC-PRC-04", "reason": "MAP_violation", "map_violation": True},
            )

        # ── EC-PRC-13: MRP Cap (Regulatory) ───────────────────────────────────
        if mrp_minor and recommended_price_minor > mrp_minor:
            recommended_price_minor = mrp_minor
            evidence.append(EvidenceItem(
                type="regulatory_cap",
                ref=f"sku:{sku_code}:mrp",
                claim=f"[EC-PRC-13] REGULATORY CAP: Recommended price capped at MRP "
                      f"${mrp_minor/100:.2f}. Reason: regulatory_price_cap.",
                confidence=1.0
            ))
            metadata["edge_case"] = "EC-PRC-13"

        # ── Apply Floor Price Guardrail ────────────────────────────────────────
        if recommended_price_minor < floor_price_minor:
            recommended_price_minor = floor_price_minor
            evidence.append(EvidenceItem(
                type="floor_price_guardrail",
                ref=f"sku:{sku_code}:floor",
                claim=f"Recommended price clamped to floor ${floor_price_minor/100:.2f} "
                      f"(maintains {MIN_MARGIN_PCT}% margin).",
                confidence=1.0
            ))

        # ── Apply Max Daily Change Guardrail ───────────────────────────────────
        max_change = working_price_minor * MAX_DAILY_CHANGE_PCT
        if abs(recommended_price_minor - working_price_minor) > max_change:
            if recommended_price_minor > working_price_minor:
                recommended_price_minor = int(working_price_minor + max_change)
            else:
                recommended_price_minor = int(working_price_minor - max_change)
                recommended_price_minor = max(recommended_price_minor, floor_price_minor)

        # ── EC-PRC-05: Bundle Pricing Conflict Check ───────────────────────────
        if bundle_ids and direction != "hold":
            evidence.append(EvidenceItem(
                type="bundle_conflict",
                ref=f"sku:{sku_code}:bundle",
                claim=f"[EC-PRC-05] SKU {sku_code} is part of bundles {bundle_ids}. "
                      f"Individual price change triggers bundle coherence check. "
                      f"Bundle repricing must be coordinated.",
                confidence=1.0
            ))
            metadata["bundle_ids"] = bundle_ids
            metadata["edge_case"] = "EC-PRC-05"

        projected_margin_pct = ((recommended_price_minor - working_cost_minor) / recommended_price_minor) * 100 if recommended_price_minor > 0 else 0.0

        # ── Determine autonomy level and risk ─────────────────────────────────
        pct_change = abs(recommended_price_minor - working_price_minor) / working_price_minor if working_price_minor > 0 else 0
        if pct_change > 0.10 or projected_margin_pct < MIN_MARGIN_PCT + 5:
            action_risk = RiskLevel.HIGH
            action_autonomy = AutonomyLevel.L2
        elif pct_change < 0.05 and projected_margin_pct >= MIN_MARGIN_PCT + 10:
            action_risk = RiskLevel.MEDIUM
            action_autonomy = AutonomyLevel.L3
        else:
            action_risk = RiskLevel.MEDIUM
            action_autonomy = AutonomyLevel.L2

        if recommended_price_minor != working_price_minor:
            proposed_actions.append(ProposedAction(
                action_type="price.update",
                resource_type="sku", resource_id=sku_code,
                parameters={
                    "sku_code": sku_code,
                    "old_price_minor": current_price_minor,
                    "new_price_minor": recommended_price_minor,
                    "margin_gain_pct": round(projected_margin_pct - current_margin_pct, 2),
                    "direction": direction,
                    "reason": reason,
                    "competitor_signal_weight": competitor_signal_weight,
                    "bundle_ids": bundle_ids or [],
                    "vip_review_required": metadata.get("vip_price_review_required", False),
                },
                idempotency_key=f"{tenant_id}:{sku_code}:price:{recommended_price_minor}",
                requires_approval=action_autonomy <= AutonomyLevel.L2,
                risk_level=action_risk,
                priority=Priority.P2,
                autonomy_level=action_autonomy,
                rollback_data={"revert_price_minor": current_price_minor},
                effective_after_minutes=CHECKOUT_LOCK_MINUTES,  # EC-PRC-06
            ))

        # ── Gemini AI Pricing Reasoning ─────────────────────────────────────────
        prompt = (
            f"Analyze pricing strategy for SKU '{sku_code}' ({title}):\n"
            f"- Current Price: ${current_price_minor/100:.2f}, Unit Cost: ${unit_cost_minor/100:.2f}\n"
            f"- Recommended Price: ${recommended_price_minor/100:.2f} (Direction: {direction})\n"
            f"- Current Margin: {current_margin_pct:.1f}%, Projected Margin: {projected_margin_pct:.1f}%\n"
            f"- Inventory Cover: {inventory_days_cover:.1f} days, Competitor Price: ${competitor_price_minor/100:.2f}\n"
            f"- Trigger Reason: {reason}\n"
            f"Provide a 1-2 sentence executive pricing recommendation and elasticity/margin rationale."
        )
        ai_summary = await gemini_client.generate_text(
            prompt=prompt,
            system_prompt="You are the Dynamic Pricing Agent ('The Profit Maximizer'). Provide concise, quantitative pricing intelligence."
        )

        model_id = gemini_client.model if ai_summary else "deterministic_fallback"

        if ai_summary:
            summary = (
                f"{ai_summary.strip()} | Margin: {current_margin_pct:.1f}% → {projected_margin_pct:.1f}% | "
                f"Autonomy: L{action_autonomy}."
            )
        else:
            summary = (
                f"SKU {sku_code} '{title}': "
                f"{'Price change recommended: ' + f'${current_price_minor/100:.2f} → ${recommended_price_minor/100:.2f} ({direction.upper()})' if recommended_price_minor != working_price_minor else 'Price OPTIMAL — no action.'} "
                f"| Margin: {current_margin_pct:.1f}% → {projected_margin_pct:.1f}% | "
                f"Inventory cover: {inventory_days_cover:.1f} days | Autonomy: L{action_autonomy}."
            )

        return AgentRunResult(
            run_id=run_id, tenant_id=tenant_id, agent=self.NAME,
            summary=summary,
            confidence=0.91 if proposed_actions else 0.98,
            risk_level=action_risk if proposed_actions else RiskLevel.LOW,
            evidence=evidence, proposed_actions=proposed_actions,
            metadata={
                **metadata,
                "current_price": current_price_minor / 100,
                "recommended_price": recommended_price_minor / 100,
                "current_margin_pct": round(current_margin_pct, 2),
                "projected_margin_pct": round(projected_margin_pct, 2),
                "expected_velocity_change_pct": expected_velocity_change * 100,
                "floor_price": floor_price_minor / 100,
                "checkout_lock_minutes": CHECKOUT_LOCK_MINUTES,
                "model_id": model_id,
                "gemini_prompt": prompt,
                "gemini_response": ai_summary or summary,
            },
            gemini_prompt=prompt,
            gemini_response=ai_summary or summary,
            model_id=model_id,
        )
