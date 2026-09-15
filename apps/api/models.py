import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, DateTime,
    ForeignKey, Text, JSON, Numeric
)
from sqlalchemy.orm import relationship
from apps.api.database import Base

def gen_uuid() -> str:
    return str(uuid.uuid4())

def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="active")
    default_currency = Column(String(3), nullable=False, default="USD")
    timezone = Column(String(50), nullable=False, default="UTC")
    created_at = Column(DateTime, nullable=False, default=now_utc)

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    cognito_sub = Column(String(255), unique=True, nullable=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default="operator")  # admin, operator, approver, analyst, viewer, customer
    created_at = Column(DateTime, nullable=False, default=now_utc)

class Product(Base):
    __tablename__ = "products"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    external_id = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="active")
    product_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)
    skus = relationship("SKU", back_populates="product", cascade="all, delete-orphan")

class SKU(Base):
    __tablename__ = "skus"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    code = Column(String(100), nullable=False)
    cost_minor = Column(BigInteger, nullable=True, default=0)
    price_minor = Column(BigInteger, nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="USD")
    weight_grams = Column(Integer, nullable=True, default=0)
    active = Column(Boolean, nullable=False, default=True)
    product = relationship("Product", back_populates="skus")
    inventory_levels = relationship("InventoryLevel", back_populates="sku")
    reservations = relationship("InventoryReservation", back_populates="sku")

class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    external_id = Column(String(100), nullable=True)
    name = Column(String(255), nullable=False)
    country_code = Column(String(2), nullable=False, default="US")
    timezone = Column(String(50), nullable=False, default="UTC")

class InventoryLevel(Base):
    __tablename__ = "inventory_levels"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    sku_id = Column(String(36), ForeignKey("skus.id"), nullable=False)
    warehouse_id = Column(String(36), ForeignKey("warehouses.id"), nullable=False)
    on_hand = Column(Integer, nullable=False, default=0)
    reserved = Column(Integer, nullable=False, default=0)
    inbound = Column(Integer, nullable=False, default=0)
    reorder_point = Column(Integer, nullable=False, default=0)
    daily_velocity = Column(Numeric(10, 2), nullable=False, default=1.0)
    updated_at = Column(DateTime, nullable=False, default=now_utc)
    sku = relationship("SKU", back_populates="inventory_levels")

class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    sku_id = Column(String(36), ForeignKey("skus.id"), nullable=False)
    user_id = Column(String(36), nullable=True)
    session_id = Column(String(100), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    locked_price_minor = Column(BigInteger, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="active")  # active, consumed, expired, released
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    sku = relationship("SKU", back_populates="reservations")

class Customer(Base):
    __tablename__ = "customers"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    external_id = Column(String(100), nullable=False)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)
    consent = Column(JSON, default=dict)
    attributes = Column(JSON, default=dict)
    created_at = Column(DateTime, nullable=False, default=now_utc)

class Order(Base):
    __tablename__ = "orders"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    external_id = Column(String(100), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    payment_status = Column(String(50), nullable=False, default="paid")
    fulfillment_status = Column(String(50), nullable=False, default="unfulfilled")
    total_minor = Column(BigInteger, nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="USD")
    shipping_address = Column(Text, nullable=True)
    ordered_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc)
    items = relationship("OrderItem", back_populates="order")
    shipments = relationship("Shipment", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    sku_id = Column(String(36), ForeignKey("skus.id"), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price_minor = Column(BigInteger, nullable=False, default=0)
    discount_minor = Column(BigInteger, nullable=False, default=0)
    order = relationship("Order", back_populates="items")

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    lead_time_days = Column(Integer, nullable=False, default=7)
    minimum_order_minor = Column(BigInteger, nullable=True, default=0)
    terms = Column(JSON, default=dict)

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    status = Column(String(50), nullable=False, default="draft")
    total_minor = Column(BigInteger, nullable=True, default=0)
    currency = Column(String(3), nullable=False, default="USD")
    expected_at = Column(DateTime, nullable=True)
    external_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)

class Shipment(Base):
    __tablename__ = "shipments"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    carrier = Column(String(100), nullable=True)
    service = Column(String(100), nullable=True)
    tracking_number = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="in_transit")
    estimated_delivery_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    cost_minor = Column(BigInteger, nullable=True, default=0)
    currency = Column(String(3), nullable=False, default="USD")
    updated_at = Column(DateTime, nullable=False, default=now_utc)
    order = relationship("Order", back_populates="shipments")

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    external_id = Column(String(100), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)
    subject = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="open")  # open, pending_approval, resolved
    priority = Column(String(50), nullable=False, default="medium")  # low, medium, high, urgent
    intent = Column(String(100), nullable=True)
    sentiment = Column(String(50), nullable=True)
    draft_reply = Column(Text, nullable=True)
    confidence = Column(Numeric(5, 4), nullable=True)
    assigned_to = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc)

class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    sku_id = Column(String(36), ForeignKey("skus.id"), nullable=False)
    old_price_minor = Column(BigInteger, nullable=True)
    new_price_minor = Column(BigInteger, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    reason = Column(Text, nullable=True)
    action_id = Column(String(36), nullable=True)
    effective_at = Column(DateTime, nullable=False, default=now_utc)

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False, default="Marketing Campaign")
    external_id = Column(String(100), nullable=True)
    channel = Column(String(100), nullable=False, default="google_ads")
    status = Column(String(50), nullable=False, default="active")  # active, paused, archived
    budget_minor = Column(BigInteger, nullable=True, default=0)
    currency = Column(String(3), nullable=False, default="USD")
    definition = Column(JSON, default=dict)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)

class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default="pending")  # pending, published, failed
    created_at = Column(DateTime, nullable=False, default=now_utc)

class NormalizedEvent(Base):
    __tablename__ = "normalized_events"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    source = Column(String(100), nullable=False)
    source_event_id = Column(String(100), nullable=False)
    schema_version = Column(Integer, nullable=False, default=1)
    payload = Column(JSON, nullable=False, default=dict)
    occurred_at = Column(DateTime, nullable=False, default=now_utc)
    received_at = Column(DateTime, nullable=False, default=now_utc)

class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    event_id = Column(String(36), ForeignKey("normalized_events.id"), nullable=True)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="running")  # running, succeeded, failed
    model_id = Column(String(100), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    input_hash = Column(String(64), nullable=False, default="none")
    result = Column(JSON, nullable=True)
    confidence = Column(Numeric(5, 4), nullable=True)
    tokens_input = Column(Integer, nullable=False, default=0)
    tokens_output = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=True)
    error_code = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=False, default=now_utc)
    completed_at = Column(DateTime, nullable=True)
    actions = relationship("ActionProposal", back_populates="agent_run")

class ActionProposal(Base):
    __tablename__ = "action_proposals"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    agent_run_id = Column(String(36), ForeignKey("agent_runs.id"), nullable=False)
    action_type = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=False)
    parameters = Column(JSON, nullable=False, default=dict)
    risk_level = Column(String(50), nullable=False, default="medium")  # low, medium, high, critical
    status = Column(String(50), nullable=False, default="pending_approval")  # pending_approval, approved, rejected, executed, failed, rolled_back
    idempotency_key = Column(String(255), nullable=False)
    requires_approval = Column(Boolean, nullable=False, default=True)
    policy_result = Column(JSON, nullable=False, default=dict)
    rollback_data = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    evidence = Column(JSON, nullable=True, default=list)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    agent_run = relationship("AgentRun", back_populates="actions")
    approvals = relationship("Approval", back_populates="action")

class Approval(Base):
    __tablename__ = "approvals"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    action_id = Column(String(36), ForeignKey("action_proposals.id"), nullable=False)
    decision = Column(String(50), nullable=False)  # approved, rejected
    decided_by = Column(String(100), nullable=False)
    reason = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=False, default=now_utc)
    action = relationship("ActionProposal", back_populates="approvals")

class ActionExecution(Base):
    __tablename__ = "action_executions"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    action_id = Column(String(36), ForeignKey("action_proposals.id"), nullable=False)
    attempt = Column(Integer, nullable=False, default=1)
    status = Column(String(50), nullable=False, default="succeeded")
    provider = Column(String(100), nullable=False)
    request_redacted = Column(JSON, nullable=True)
    response_redacted = Column(JSON, nullable=True)
    external_reference = Column(String(255), nullable=True)
    started_at = Column(DateTime, nullable=False, default=now_utc)
    completed_at = Column(DateTime, nullable=True)

class Policy(Base):
    __tablename__ = "policies"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    policy_type = Column(String(100), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    enabled = Column(Boolean, nullable=False, default=True)
    document = Column(JSON, nullable=False, default=dict)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    title = Column(String(255), nullable=False)
    source_uri = Column(String(500), nullable=False)
    content_hash = Column(String(64), nullable=False)
    status = Column(String(50), nullable=False, default="indexed")
    doc_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, nullable=False, default=now_utc)

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("knowledge_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=False)
    chunk_metadata = Column("metadata", JSON, default=dict)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    actor_type = Column(String(50), nullable=False)  # agent, user, system
    actor_id = Column(String(100), nullable=False)
    operation = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    before_data = Column(JSON, nullable=True)
    after_data = Column(JSON, nullable=True)
    correlation_id = Column(String(100), nullable=False)
    ip_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)
