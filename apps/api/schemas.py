from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# Base schemas
class TenantBase(BaseModel):
    name: str
    default_currency: str = "USD"
    timezone: str = "UTC"

class EvidenceItem(BaseModel):
    type: str = "metric"  # metric, rule, document, log
    ref: str
    claim: str

class ProposedActionPayload(BaseModel):
    action_type: str
    resource_type: str
    resource_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str
    requires_approval: bool = True
    risk_level: str = "medium"
    summary: Optional[str] = None
    evidence: List[EvidenceItem] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    rollback_data: Optional[Dict[str, Any]] = None

class ActionApprovalRequest(BaseModel):
    decision: str = "approved"  # approved or rejected
    decided_by: str = "operator@example.com"
    reason: Optional[str] = None

class ActionProposalResponse(BaseModel):
    id: str
    tenant_id: str
    agent_run_id: str
    action_type: str
    resource_type: str
    resource_id: str
    parameters: Dict[str, Any]
    risk_level: str
    status: str
    requires_approval: bool
    summary: Optional[str]
    evidence: Optional[List[Dict[str, Any]]]
    policy_result: Dict[str, Any]
    created_at: datetime
    class Config:
        from_attributes = True

class AgentRunResponse(BaseModel):
    id: str
    agent_name: str
    status: str
    confidence: Optional[float]
    summary: Optional[str] = None
    latency_ms: Optional[int]
    tokens_input: int
    tokens_output: int
    started_at: datetime
    completed_at: Optional[datetime]
    actions: List[ActionProposalResponse] = []
    class Config:
        from_attributes = True

class InventoryRiskItem(BaseModel):
    sku_id: str
    sku_code: str
    product_title: str
    on_hand: int
    reserved: int
    net_available: int
    reorder_point: int
    daily_velocity: float
    days_of_cover: float
    status: str  # healthy, warning, critical
    supplier_name: Optional[str]
    supplier_lead_time: Optional[int]

class OrderExceptionItem(BaseModel):
    order_id: str
    external_id: str
    status: str
    payment_status: str
    fulfillment_status: str
    total_amount: float
    currency: str
    exception_type: str
    ordered_at: datetime
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None

class SupportTicketItem(BaseModel):
    ticket_id: str
    external_id: str
    customer_email: Optional[str]
    subject: Optional[str]
    message: Optional[str]
    status: str
    priority: str
    intent: Optional[str]
    sentiment: Optional[str]
    draft_reply: Optional[str]
    confidence: Optional[float]
    created_at: datetime

class PricingRecommendationItem(BaseModel):
    sku_id: str
    sku_code: str
    title: str
    current_price: float
    cost: float
    current_margin_pct: float
    recommended_price: float
    projected_margin_pct: float
    expected_unit_change_pct: float
    reason: str
    confidence: float

class DashboardSummaryResponse(BaseModel):
    revenue_today_minor: int
    active_orders_count: int
    critical_stockouts_count: int
    pending_approvals_count: int
    open_tickets_count: int
    active_agents_count: int
    system_health: str
    savings_estimated_usd: float
    autonomy_distribution: Dict[str, int]
    recent_agent_runs: List[AgentRunResponse]
    pending_actions: List[ActionProposalResponse]
