"""
brain/shared/policy_engine.py
Full P0-P3 Priority Conflict Resolution + L0-L4 Autonomy Policy Engine
Covers all 16 Orchestrator edge cases from ALL_7_AGENTS_ENTERPRISE_SPEC.md
"""
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
from brain.shared.contracts import (
    ProposedAction, PolicyResult, Priority, RiskLevel,
    AutonomyLevel, PolicyDecision
)


# ─────────────────────────────────────────────────────────────────────────────
# P0-P3 Priority Definitions
# ─────────────────────────────────────────────────────────────────────────────

# Actions that carry P0 (Safety) priority — override EVERYTHING
P0_ACTION_TYPES: Set[str] = {
    "inventory.critical_hold",
    "campaign.pause",            # When triggered by P0 inventory hold
    "price.hold",                # When triggered by P0 inventory hold
    "order.fraud_hold",          # EC-ORD-05: COD fraud hold
    "ticket.security_escalate",  # EC-SUP-05: Prompt injection
    "ticket.chargeback_escalate",# EC-SUP-07: Chargeback P0
    "supplier.compliance_block", # EC-INV-10: Blocked supplier
}

# Actions that carry P1 (SLA) priority — override P2, P3
P1_ACTION_TYPES: Set[str] = {
    "order.priority_escalate",
    "carrier.reroute",           # When driven by VIP SLA breach
    "shipment.expedite",
    "ticket.vip_escalate",       # EC-SUP-13: VIP SLA breach
}

# Actions requiring mandatory human approval regardless of autonomy level
ALWAYS_APPROVE_ACTIONS: Set[str] = {
    "purchase_order.create",
    "order.refund",
    "order.cancel",
    "campaign.send",             # EC-MKT — ALWAYS L2
    "price.update",              # When >10% or margin near floor
    "carrier.reroute",           # When cost delta > auto limit
    "supplier.contract_modify",
    "customer.account_suspend",
}

# Actions that can auto-execute at L3+ if confidence threshold met
L3_AUTO_EXECUTE_ACTIONS: Set[str] = {
    "campaign.pause",            # Protective action — safe to auto-execute
    "price.hold",                # Protective action
    "price.lock",                # EC-PRC-06: Checkout session price lock
    "support.send_reply",        # When confidence >= 0.90
    "order.priority_escalate",   # Flagging/internal action
    "ticket.tag",                # Internal tagging
    "ticket.tag_update",         # Internal tagging
    "inventory.tag",             # Internal tagging
    "inventory.reserve",         # EC-INV-13: Concurrent DB write / reservation
    "order.confirm",             # When payment confirmed + stock available
    "notification.send",         # Customer notification (non-financial)
    "ticket.deduplicate",        # EC-SUP-09: Duplicate ticket deduplication
    "kb.invalidate_cache",       # EC-SUP-12: Stale knowledge base invalidation
    "shipment.inter_warehouse_transfer", # EC-LOG-05: Balancing transfer
}

# L4 fully autonomous actions (internal state only, no external effects)
L4_AUTO_ACTIONS: Set[str] = {
    "ticket.tag",
    "inventory.tag",
    "order.internal_flag",
    "campaign.segment_update",
}

# Financial auto-approval limit (minor units)
DEFAULT_AUTO_MONEY_LIMIT_MINOR = 5000   # $50.00
VIP_AUTO_REFUND_LIMIT_MINOR = 2500      # $25.00
HIGH_VALUE_ORDER_THRESHOLD_MINOR = 10000  # $100.00
NL_COMMAND_IMPACT_THRESHOLD_MINOR = 5000000  # $50,000 — EC-ORC-05

# Agent timeout for deadlock prevention (EC-ORC-01)
AGENT_TIMEOUT_SECONDS = 30

# Max event loop count before circuit breaker (EC-ORC-11)
MAX_LOOP_COUNT = 3

# Rate limiting per event type (EC-ORC-03)
MAX_EVENTS_PER_MINUTE_PER_TYPE = 50


class PolicyEngine:
    """
    Deterministic authorization and policy validation engine.
    Implements all rules from ALL_7_AGENTS_ENTERPRISE_SPEC.md:
    - L0-L4 Autonomy Level evaluation
    - P0-P3 Priority Conflict Resolution
    - Financial thresholds
    - Idempotency checks
    - Event loop detection
    - NL command safety guardrails
    - Action expiry monitoring
    """

    @staticmethod
    def evaluate(
        action: ProposedAction,
        tenant_id: str,
        autonomy_level: int = AutonomyLevel.L2,
        p0_hold_active: bool = False,
        p0_hold_skus: Optional[List[str]] = None,
        agent_confidence: float = 0.85,
        is_nl_command: bool = False,
        nl_financial_impact_minor: int = 0,
    ) -> PolicyResult:
        """
        Evaluate a proposed action against all enterprise policy rules.
        Returns a PolicyResult with APPROVED / PENDING_APPROVAL / REJECTED.
        """
        p0_hold_skus = p0_hold_skus or []

        # ── RULE 0: Idempotency key is mandatory (EC-ORC-15) ──────────────────
        if not action.idempotency_key or not action.idempotency_key.strip():
            return PolicyResult(
                decision=PolicyDecision.REJECTED,
                reason="RULE-0: Missing mandatory idempotency key. Every action must have a deterministic idempotency_key.",
                requires_approval=False,
            )

        # ── RULE 1: Action expiry check (EC-ORC-14) ──────────────────────────
        if action.expires_at and datetime.now(timezone.utc) > action.expires_at.replace(tzinfo=timezone.utc):
            return PolicyResult(
                decision=PolicyDecision.REJECTED,
                reason=f"RULE-1: Action expired at {action.expires_at.isoformat()}. A fresh evaluation is required.",
                requires_approval=False,
            )

        # ── RULE 2: P0 Inventory Hold — freeze discounts + marketing ─────────
        # (EC-INV-01, EC-PRC-03, EC-MKT-01)
        if p0_hold_active and p0_hold_skus:
            sku_in_hold = any(
                str(sku) in str(action.parameters.get("sku_code", ""))
                or str(sku) in str(action.resource_id)
                for sku in p0_hold_skus
            )
            if sku_in_hold:
                discount_actions = {"price.update", "campaign.send", "campaign.discount"}
                if action.action_type in discount_actions:
                    # Extract if it's a discount (negative margin_gain or discount type)
                    margin_gain = action.parameters.get("margin_gain_pct", 0)
                    new_price = action.parameters.get("new_price_minor", 999999)
                    old_price = action.parameters.get("old_price_minor", 999999)
                    is_discount = margin_gain < 0 or new_price < old_price
                    if is_discount:
                        return PolicyResult(
                            decision=PolicyDecision.REJECTED,
                            reason=f"RULE-2 [P0 OVERRIDE]: P0 inventory hold active for SKU. "
                                   f"Discount action '{action.action_type}' blocked. "
                                   f"P0 Safety > P3 Growth. Hold must be lifted first.",
                            requires_approval=False,
                            priority=Priority.P0,
                            conflict_resolved_by="P0_inventory_overrides_P3_marketing",
                        )

        # ── RULE 3: NL Command High-Impact Guard (EC-ORC-05) ─────────────────
        if is_nl_command and nl_financial_impact_minor > NL_COMMAND_IMPACT_THRESHOLD_MINOR:
            return PolicyResult(
                decision=PolicyDecision.PENDING_APPROVAL,
                reason=f"RULE-3 [NL GUARD]: Natural language command has financial impact "
                       f"${nl_financial_impact_minor/100:,.2f} which exceeds "
                       f"${NL_COMMAND_IMPACT_THRESHOLD_MINOR/100:,.2f} auto-limit. "
                       f"Mandatory human confirmation regardless of autonomy level.",
                requires_approval=True,
                priority=Priority.P0,
            )

        # ── RULE 4: Critical risk always requires human approval ──────────────
        if action.risk_level == RiskLevel.CRITICAL:
            return PolicyResult(
                decision=PolicyDecision.PENDING_APPROVAL,
                reason=f"RULE-4: CRITICAL risk level requires mandatory human sign-off.",
                requires_approval=True,
                priority=Priority.P1,
            )

        # ── RULE 5: HIGH risk + L0-L2 → approval required ────────────────────
        if action.risk_level == RiskLevel.HIGH and autonomy_level < AutonomyLevel.L3:
            return PolicyResult(
                decision=PolicyDecision.PENDING_APPROVAL,
                reason=f"RULE-5: HIGH risk action at autonomy level L{autonomy_level} requires human review.",
                requires_approval=True,
                priority=Priority.P1,
            )

        # ── RULE 6: ALWAYS-APPROVE actions at L0-L1 ──────────────────────────
        if action.action_type in ALWAYS_APPROVE_ACTIONS:
            # Special case for fx_drift in price.update: if fx_drift_pct is provided and autonomy_level >= L3, allow auto-execution
            if action.action_type == "price.update" and "fx_drift_pct" in action.parameters and autonomy_level >= AutonomyLevel.L3:
                pass
            else:
                money_amount = (
                    action.parameters.get("total_minor")
                    or action.parameters.get("amount_minor")
                    or action.parameters.get("refund_amount_minor")
                    or 0
                )
                return PolicyResult(
                    decision=PolicyDecision.PENDING_APPROVAL,
                    reason=f"RULE-6: Action '{action.action_type}' is classified as always-require-approval "
                           f"(financial amount: ${money_amount/100:,.2f}). Human sign-off mandatory.",
                    requires_approval=True,
                    priority=action.priority,
                )

        # ── RULE 7: Monetary threshold check ──────────────────────────────────
        money_amount = (
            action.parameters.get("total_minor")
            or action.parameters.get("amount_minor")
            or action.parameters.get("refund_amount_minor")
            or 0
        )
        if money_amount > DEFAULT_AUTO_MONEY_LIMIT_MINOR:
            return PolicyResult(
                decision=PolicyDecision.PENDING_APPROVAL,
                reason=f"RULE-7: Monetary amount ${money_amount/100:,.2f} exceeds auto-approval limit "
                       f"${DEFAULT_AUTO_MONEY_LIMIT_MINOR/100:,.2f}. Human approval required.",
                requires_approval=True,
                priority=Priority.P2,
            )

        # ── RULE 8: L3 Auto-execute with confidence check ─────────────────────
        if autonomy_level >= AutonomyLevel.L3:
            if action.action_type in L3_AUTO_EXECUTE_ACTIONS or (action.action_type == "price.update" and "fx_drift_pct" in action.parameters):
                if agent_confidence >= 0.85:
                    return PolicyResult(
                        decision=PolicyDecision.APPROVED,
                        reason=f"RULE-8: Auto-approved at L{autonomy_level} — "
                               f"action '{action.action_type}' is guardrailed with confidence={agent_confidence:.2f}.",
                        requires_approval=False,
                        priority=action.priority,
                    )
                else:
                    return PolicyResult(
                        decision=PolicyDecision.PENDING_APPROVAL,
                        reason=f"RULE-8b: L{autonomy_level} confidence {agent_confidence:.2f} below threshold 0.85. "
                               f"Escalating for human review.",
                        requires_approval=True,
                        priority=Priority.P2,
                    )

        # ── RULE 9: L4 Fully Autonomous (internal actions only) ───────────────
        if autonomy_level >= AutonomyLevel.L4:
            if action.action_type in L4_AUTO_ACTIONS:
                return PolicyResult(
                    decision=PolicyDecision.APPROVED,
                    reason=f"RULE-9: Fully autonomous execution at L4 for internal action '{action.action_type}'.",
                    requires_approval=False,
                    priority=Priority.P3,
                )

        # ── RULE 10: Default safety — pending human approval ──────────────────
        return PolicyResult(
            decision=PolicyDecision.PENDING_APPROVAL,
            reason="RULE-10: Default safety policy — pending human approval.",
            requires_approval=True,
            priority=action.priority,
        )

    @staticmethod
    def resolve_conflict(
        actions: List[ProposedAction],
        p0_hold_skus: Optional[List[str]] = None,
    ) -> List[PolicyResult]:
        """
        EC-ORC-06: Resolve conflicts between actions in the same agent run.
        Applies P0 > P1 > P2 > P3 priority matrix.
        Returns a result per action, with conflict annotations.
        """
        p0_hold_skus = p0_hold_skus or []
        results = []

        # Detect SKU-level conflicts (same SKU, opposing actions)
        sku_actions: Dict[str, List[ProposedAction]] = {}
        for action in actions:
            sku = action.parameters.get("sku_code") or action.resource_id
            if sku not in sku_actions:
                sku_actions[sku] = []
            sku_actions[sku].append(action)

        # Find conflicting SKU pairs
        conflicting_skus: Set[str] = set()
        for sku, sku_action_list in sku_actions.items():
            if len(sku_action_list) > 1:
                has_price_up = any(
                    a.action_type == "price.update" and a.parameters.get("margin_gain_pct", 0) > 0
                    for a in sku_action_list
                )
                has_discount = any(
                    a.action_type in {"campaign.send", "price.update", "campaign.discount"}
                    and (a.parameters.get("margin_gain_pct", 0) < 0
                         or a.parameters.get("new_price_minor", 999999) < a.parameters.get("old_price_minor", 0))
                    for a in sku_action_list
                )
                if has_price_up and has_discount:
                    conflicting_skus.add(sku)

        for action in actions:
            sku = action.parameters.get("sku_code") or action.resource_id
            if sku in conflicting_skus:
                # P0 wins: if P0 hold active for this SKU, block discount
                p0_active = sku in p0_hold_skus
                priority_order = {Priority.P0: 0, Priority.P1: 1, Priority.P2: 2, Priority.P3: 3}
                action_priority = priority_order.get(action.priority, 2)

                if p0_active and action_priority >= 2:
                    results.append(PolicyResult(
                        decision=PolicyDecision.REJECTED,
                        reason=f"CONFLICT-RESOLUTION: P0 inventory hold overrides {action.priority} action "
                               f"'{action.action_type}' for SKU {sku}.",
                        requires_approval=False,
                        priority=Priority.P0,
                        conflict_resolved_by="P0_inventory_wins",
                    ))
                else:
                    results.append(PolicyResult(
                        decision=PolicyDecision.PENDING_APPROVAL,
                        reason=f"CONFLICT-RESOLUTION: SKU {sku} has conflicting actions (price↑ vs discount). "
                               f"Consolidated for human review.",
                        requires_approval=True,
                        priority=action.priority,
                        conflict_resolved_by="conflict_package_human_review",
                    ))
            else:
                # No conflict — apply standard evaluation
                results.append(PolicyEngine.evaluate(action, "", p0_hold_active=bool(p0_hold_skus), p0_hold_skus=p0_hold_skus))

        return results

    evaluate_proposed_action = evaluate

    @staticmethod
    def resolve_conflicts(actions: List[ProposedAction], p0_hold_skus: Optional[List[str]] = None) -> List[ProposedAction]:
        """Alias returning sorted actions by priority for resolve_conflicts."""
        priority_order = {Priority.P0: 0, Priority.P1: 1, Priority.P2: 2, Priority.P3: 3}
        return sorted(actions, key=lambda a: priority_order.get(a.priority, 2))

    @staticmethod
    def check_event_loop(correlation_id: str = "", loop_count: int = 0, hop_count: Optional[int] = None) -> bool:
        """
        EC-ORC-11: Detect agent event loops.
        Returns True if circuit breaker should open.
        """
        count = hop_count if hop_count is not None else loop_count
        return count >= MAX_LOOP_COUNT

    @staticmethod
    def check_agent_health(last_heartbeat_seconds_ago: int = 0, seconds_since_last_run: Optional[int] = None) -> str:
        """
        EC-ORC-02: Determine agent health status from heartbeat age.
        Returns: 'healthy', 'timed_out', 'degraded', 'dead'
        """
        seconds = seconds_since_last_run if seconds_since_last_run is not None else last_heartbeat_seconds_ago
        if seconds <= 30:
            return "healthy"
        elif seconds <= 60:
            return "degraded"
        elif seconds <= 120:
            return "timed_out"
        return "dead"

    @staticmethod
    def check_approval_queue_overflow(pending_count: int, oldest_pending_hours: float) -> Dict[str, Any]:
        """
        EC-ORC-04: Detect human approval queue overflow requiring escalation.
        Returns Dict with escalation flags.
        """
        overflow = pending_count > 100 and oldest_pending_hours > 4.0
        return {
            "escalate_to_vp": overflow,
            "pending_count": pending_count,
            "oldest_pending_hours": oldest_pending_hours,
        }

    @staticmethod
    def validate_nl_command(command: str, estimated_financial_impact_minor: int) -> tuple[bool, str]:
        """
        EC-ORC-05: Enforce financial safety limits on natural language commands.
        """
        if estimated_financial_impact_minor > NL_COMMAND_IMPACT_THRESHOLD_MINOR:
            return False, f"Command financial impact ${estimated_financial_impact_minor/100:,.2f} exceeds limit ${NL_COMMAND_IMPACT_THRESHOLD_MINOR/100:,.2f}"
        return True, "Valid"

    @staticmethod
    def check_pool_starvation(active_connections: int, max_pool_size: int = 20) -> Dict[str, Any]:
        """
        EC-ORC-14: Database Connection Pool Starvation Guard
        """
        is_starved = active_connections >= (max_pool_size - 1)
        return {
            "shed_non_essential": is_starved,
            "active_connections": active_connections,
            "max_pool_size": max_pool_size,
        }

