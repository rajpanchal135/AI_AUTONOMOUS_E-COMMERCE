"""
brain/shared/contracts.py
Enterprise-grade shared data contracts for all 7 agents.
Supports all 112 edge cases defined in ALL_7_AGENTS_ENTERPRISE_SPEC.md
"""
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AutonomyLevel(int, Enum):
    L0 = 0  # Observe & Alert Only
    L1 = 1  # Recommend + Draft Action
    L2 = 2  # Propose + Mandatory Human Approval
    L3 = 3  # Guardrailed Auto-Execute
    L4 = 4  # Fully Autonomous


class Priority(str, Enum):
    P0 = "P0"  # Safety & Inventory Guardrails — wins over everything
    P1 = "P1"  # Order Fulfillment & SLA
    P2 = "P2"  # Dynamic Margin Optimization
    P3 = "P3"  # Growth & Marketing Campaigns


class PolicyDecision(str, Enum):
    APPROVED = "APPROVED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    REJECTED = "REJECTED"


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    WAITLIST = "waitlist"
    PENDING_MANUAL_REVIEW = "pending_manual_review"
    PENDING_COMPLIANCE_REVIEW = "pending_compliance_review"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIAL_REFUND = "partial_refund"
    CHARGEBACK = "chargeback"


class CustomerSegment(str, Enum):
    VIP = "vip"
    CHAMPION = "champion"
    LOYAL = "loyal"
    AT_RISK = "at_risk"
    WIN_BACK = "win_back"
    NEW = "new"
    SEASONAL = "seasonal"


# ─────────────────────────────────────────────────────────────────────────────
# Core Shared Models
# ─────────────────────────────────────────────────────────────────────────────

class EvidenceItem(BaseModel):
    """Grounded evidence item supporting an agent's findings or proposed action."""
    type: str  # metric, rule, document, log, carrier_api, policy_doc, supplier_data, fraud_signal
    ref: str   # Unique reference identifier for the evidence source
    claim: str # Human-readable claim supported by this evidence
    confidence: float = 1.0  # Evidence confidence score (0.0 to 1.0)
    data_freshness_minutes: Optional[int] = None  # Age of data in minutes; None = real-time


class ProposedAction(BaseModel):
    """
    A typed, policy-validated action proposed by an agent.
    No action is executed without passing through the PolicyEngine.
    """
    action_type: str           # e.g., purchase_order.create, price.update, campaign.pause
    resource_type: str         # e.g., sku, order, ticket, campaign, shipment
    resource_id: str           # The target resource's identifier
    parameters: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str       # Deterministic: {tenant_id}:{resource_id}:{action_type}:{state_hash}
    requires_approval: bool = True
    risk_level: str = RiskLevel.MEDIUM  # low, medium, high, critical
    priority: str = Priority.P2         # P0-P3 conflict resolution priority
    autonomy_level: int = AutonomyLevel.L2
    expires_at: Optional[datetime] = None
    rollback_data: Optional[Dict[str, Any]] = None
    external_rollback_required: bool = False  # EC-ORC-07: Shopify/external system rollback needed
    effective_after_minutes: int = 0          # EC-PRC-06: Checkout session price lock
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentRunResult(BaseModel):
    """
    Typed result returned by every agent execution.
    Contains findings, proposed actions, and audit metadata.
    """
    run_id: str
    tenant_id: str
    agent: str
    summary: str
    confidence: float
    risk_level: str = RiskLevel.LOW
    evidence: List[EvidenceItem] = Field(default_factory=list)
    proposed_actions: List[ProposedAction] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Cross-agent signal fields
    emits_p0_hold: bool = False          # EC-INV-01: Inventory critical hold signal
    p0_hold_sku_codes: List[str] = Field(default_factory=list)
    emits_return_surge: bool = False     # EC-INV-12: Return surge event
    model_id: str = "gemini-3.5-flash-lite"  # Active Gemini model
    prompt_version: str = "2.0"          # EC-ORC-10: Prompt version tracking
    gemini_prompt: Optional[str] = None  # Exact Google Gemini prompt sent
    gemini_response: Optional[str] = None  # Exact Google Gemini output received


# ─────────────────────────────────────────────────────────────────────────────
# Inventory Domain Models
# ─────────────────────────────────────────────────────────────────────────────

class SKUContext(BaseModel):
    """Full SKU context required for inventory + pricing edge case evaluation."""
    sku_code: str
    title: str
    on_hand: int
    reserved: int
    inbound: int
    daily_velocity: float
    unit_cost_minor: int                   # Cost in minor currency units (cents/paise)
    current_price_minor: int
    supplier_id: str = "sup-default"
    supplier_name: str = "Default Supplier"
    supplier_status: str = "active"        # EC-INV-10: blocked, active, compliance_review
    supplier_compliance_flag: bool = False  # EC-INV-10
    lead_time_days: int = 12
    last_po_delivery_actual_days: Optional[int] = None  # EC-INV-02
    lead_time_reliability_score: float = 1.0            # EC-INV-02 (<0.7 = force approval)
    # Warehouse context (EC-INV-06)
    warehouse_id: str = "wh-main"
    warehouse_capacity_remaining: Optional[int] = None
    # Budget constraint (EC-INV-05)
    budget_limit_minor: Optional[int] = None
    # Perishable / expiry (EC-INV-09)
    expiry_days: Optional[int] = None
    is_perishable: bool = False
    # SKU metadata (EC-INV-14, EC-PRC-11, EC-PRC-15)
    parent_sku: Optional[str] = None
    is_new_sku: bool = False
    is_gift_item: bool = False
    experiment_lock: bool = False          # EC-PRC-15: A/B test lock
    # Pricing guardrails (EC-PRC-04, EC-PRC-13)
    map_price_minor: Optional[int] = None  # Minimum Advertised Price
    mrp_minor: Optional[int] = None        # Maximum Retail Price (regulatory)
    price_inclusive_tax: bool = False       # EC-PRC-08
    # Bundle context (EC-PRC-05)
    bundle_ids: List[str] = Field(default_factory=list)
    # Logistics (EC-LOG-04, EC-ORD-10)
    hazmat_class: Optional[str] = None
    actual_weight_grams: Optional[int] = None
    # Seasonal (EC-INV-04)
    seasonal_multiplier: float = 1.0
    category_avg_velocity: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Order Domain Models
# ─────────────────────────────────────────────────────────────────────────────

class OrderContext(BaseModel):
    """Full order context for Order Management Agent edge cases."""
    order_id: str
    external_id: str
    tenant_id: str
    customer_id: str
    customer_segment: str = CustomerSegment.NEW
    customer_lifetime_value_minor: int = 0
    customer_refund_count_30d: int = 0        # EC-SUP-02: Repeat refund detection
    customer_gstin: Optional[str] = None       # EC-ORD-07: B2B GST
    customer_type: str = "consumer"            # consumer, business
    status: str = OrderStatus.PENDING
    payment_status: str = PaymentStatus.PENDING
    payment_method: str = "prepaid"            # prepaid, cod
    fulfillment_sub_status: Optional[str] = None  # EC-ORD-08: picking_started, etc.
    total_minor: int = 0
    captured_amount_minor: int = 0             # EC-ORD-09: FX mismatch
    currency: str = "USD"
    destination_country: str = "IN"            # EC-ORD-10: Export restrictions
    address_valid: bool = True                  # EC-ORD-02
    is_high_fraud_pincode: bool = False         # EC-ORD-05
    idempotency_key: Optional[str] = None       # EC-ORD-06
    is_duplicate: bool = False
    return_inspection_required: bool = False    # EC-ORD-13: High-value return fraud
    items: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    same_day_delivery_requested: bool = False   # EC-ORD-12
    is_international: bool = False
    # SLA
    sla_days: int = 3
    error_type: Optional[str] = None           # EC-LOG-10: wrong_item_delivered


# ─────────────────────────────────────────────────────────────────────────────
# Support Domain Models
# ─────────────────────────────────────────────────────────────────────────────

class TicketContext(BaseModel):
    """Full ticket context for Support Agent edge cases."""
    ticket_id: str
    external_id: str
    customer_id: str
    customer_email: str
    customer_segment: str = CustomerSegment.NEW
    customer_lifetime_value_minor: int = 0
    customer_refund_count_30d: int = 0   # EC-SUP-02
    message: str
    language: str = "en"                 # EC-SUP-04: Multi-language
    order_external_id: Optional[str] = None
    order_status: Optional[str] = None
    carrier_tracking: Optional[str] = None
    estimated_delivery: Optional[str] = None  # EC-SUP-01: Only verified dates
    delivered_at: Optional[datetime] = None
    refund_window_days: int = 15         # EC-SUP-10
    refund_amount_minor: int = 0
    previous_messages: List[str] = Field(default_factory=list)  # EC-SUP-15
    created_at: Optional[datetime] = None
    # Computed fields (set by agent)
    intent: Optional[str] = None
    sentiment_score: float = 0.5         # 0=negative, 1=positive
    pan_detected: bool = False           # EC-SUP-14: PII detection
    injection_detected: bool = False     # EC-SUP-05: Prompt injection


# ─────────────────────────────────────────────────────────────────────────────
# Logistics Domain Models
# ─────────────────────────────────────────────────────────────────────────────

class ShipmentContext(BaseModel):
    """Full shipment context for Logistics Agent edge cases."""
    shipment_id: str
    order_external_id: str
    order_id: str
    tenant_id: str
    carrier: str
    tracking_number: Optional[str] = None
    current_status: str = "in_transit"   # EC-LOG-01, EC-LOG-08
    delayed_hours: int = 0
    last_scan_hours_ago: int = 0         # EC-LOG-02: No scan = last-mile failure
    destination_pincode: Optional[str] = None
    destination_country: str = "IN"
    is_international: bool = False
    payment_method: str = "prepaid"      # EC-LOG-06: COD collection failure
    payment_status: str = "paid"
    is_cod: bool = False
    order_total_minor: int = 0
    insurance_threshold_minor: int = 50000  # EC-LOG-09: $500
    has_insurance: bool = False
    hazmat_class: Optional[str] = None   # EC-LOG-04
    weight_grams_listed: int = 0
    weight_grams_actual: Optional[int] = None  # EC-LOG-03
    delivery_gps_lat: Optional[float] = None   # EC-LOG-13: Fraud GPS check
    delivery_gps_long: Optional[float] = None
    address_gps_lat: Optional[float] = None
    address_gps_long: Optional[float] = None
    co2_grams_estimated: Optional[float] = None  # EC-LOG-16: Carbon
    customs_days_stuck: int = 0          # EC-LOG-14
    carrier_handoff_tracking: Optional[str] = None  # EC-LOG-12
    is_vip_customer: bool = False
    customer_segment: str = CustomerSegment.NEW
    # Carrier scoring weights (EC-LOG-11)
    cost_weight: float = 0.4
    eta_weight: float = 0.3
    reliability_weight: float = 0.2
    sustainability_weight: float = 0.1


# ─────────────────────────────────────────────────────────────────────────────
# Marketing Domain Models
# ─────────────────────────────────────────────────────────────────────────────

class CampaignContext(BaseModel):
    """Full campaign context for Marketing Agent edge cases."""
    campaign_id: str
    campaign_name: str
    tenant_id: str
    channel: str = "email"               # email, sms, push, display
    sku_codes: List[str] = Field(default_factory=list)
    segment: str = CustomerSegment.NEW
    daily_ad_spend_minor: int = 0
    inventory_days_cover: float = 30.0   # EC-MKT-01: P0 guard
    # Price alignment (EC-MKT-09)
    email_price_minor: Optional[int] = None
    current_price_minor: Optional[int] = None
    # Consent (EC-MKT-02)
    consent_verified: bool = False
    # Template (EC-MKT-14)
    template_vars: Dict[str, Any] = Field(default_factory=dict)
    template_body: str = ""
    # Performance (EC-MKT-11)
    current_ctr: float = 0.0
    current_roas: float = 0.0
    min_roas_threshold: float = 1.0
    evaluation_window_minutes: int = 240
    # SPAM (EC-MKT-16)
    spam_complaint_rate: float = 0.0
    # Budget (EC-MKT-07)
    ads_data_freshness_minutes: int = 0
    # Attribution (EC-MKT-04)
    attribution_model: str = "last_touch"  # first_touch, last_touch, linear
    # Competitor timing (EC-MKT-06)
    competitor_active_window: bool = False
    # Idempotency (EC-MKT-10)
    idempotency_key: Optional[str] = None
    # Audience (EC-MKT-13)
    audience_segments: List[str] = Field(default_factory=list)
    # Velocity surge monitoring (EC-MKT-15)
    expected_velocity: float = 0.0
    current_velocity: float = 0.0
    # Customer seasonality (EC-MKT-08)
    customer_order_seasonality: Optional[str] = None  # annual, quarterly, etc.


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator Domain Models
# ─────────────────────────────────────────────────────────────────────────────

class NormalizedEvent(BaseModel):
    """Normalized event flowing through the Orchestrator event bus."""
    event_id: str
    source_event_id: str                   # EC-ORC-15: Idempotency dedup
    event_type: str                        # inventory.stock_low, order.created, etc.
    tenant_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None   # EC-ORC-11: Event loop detection
    loop_count: int = 0                    # Increments on each recursion
    schema_version: str = "2.0"           # EC-ORC-10: Prompt version mismatch
    priority: str = Priority.P2


class PolicyResult(BaseModel):
    """Result of PolicyEngine.evaluate() for a single ProposedAction."""
    decision: str  # APPROVED, PENDING_APPROVAL, REJECTED
    reason: str
    requires_approval: bool
    priority: str = Priority.P2
    conflict_resolved_by: Optional[str] = None  # e.g., "P0_inventory_overrides_P3_marketing"

    def __getitem__(self, item: str):
        val = getattr(self, item)
        return val.value if hasattr(val, "value") else val


# ─────────────────────────────────────────────────────────────────────────────
# PII Utilities (Cross-cutting — EC-SUP-14, EC-SUP-08)
# ─────────────────────────────────────────────────────────────────────────────

PAN_REGEX = re.compile(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b')
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "system prompt",
    "reveal your",
    "print all",
    "show me all",
    "you are now",
    "disregard",
]


def redact_pan(text: str) -> tuple[str, bool]:
    """Redact credit card PANs from text. Returns (redacted_text, was_detected)."""
    detected = bool(PAN_REGEX.search(text))
    redacted = PAN_REGEX.sub("**** **** **** [REDACTED_PAN]", text)
    return redacted, detected


def detect_prompt_injection(text: str) -> bool:
    """Detect common prompt injection patterns in customer messages."""
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in INJECTION_PATTERNS)
