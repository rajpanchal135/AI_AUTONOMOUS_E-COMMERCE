# Multi-Agent Specification Cards

## 1. Supervisor Agent
- **Purpose**: Routes incoming commerce events to specialist agents, executes safe parallel tasks, and synthesizes action proposals.
- **Trigger Events**: `inventory.stock_low`, `order.created`, `order.shipment_delayed`, `ticket.created`, `schedule.daily`.
- **Conflict Policy**: Safety & compliance > tenant policy > margin protection > customer experience > growth optimization.

## 2. Inventory Agent
- **Purpose**: Computes stock runout velocity, supplier lead time, and safety stock. Generates MOQ-aligned replenishment purchase orders.
- **Core Formula**: `reorder_point = (daily_velocity × lead_time_days) + (service_factor × stddev × sqrt(lead_time))`.
- **Proposed Actions**: `purchase_order.create`, `inventory.transfer`.

## 3. Order Operations Agent
- **Purpose**: Detects fulfillment SLA breaches, payment anomalies, and stale shipments.
- **Proposed Actions**: `order.notify_delay`, `order.hold`, `order.release`, `order.split_shipment`.

## 4. Support Agent (RAG)
- **Purpose**: Grounded retrieval over carrier APIs, return policies, and FAQs. Drafts verified customer replies without hallucinating ETAs.
- **Confidence Gates**:
  - `≥ 0.90`: Eligible for automated tagging and draft generation.
  - `0.75 – 0.89`: Staged for human review.
  - `< 0.75`: Escalated to senior support operator.
- **Proposed Actions**: `support.send_reply`, `support.tag_update`, `order.refund` (subject to money limits).

## 5. Pricing Agent
- **Purpose**: Optimizes contribution margin subject to elasticity and business guardrails.
- **Guardrails**: Minimum 30% gross margin; max 10% move per 24 hours; rollback snapshot recorded.
- **Proposed Actions**: `price.update`.

## 6. Marketing Agent
- **Purpose**: Aligns advertising budget with inventory availability to prevent ad spend waste on stocking-out SKUs.
- **Proposed Actions**: `campaign.pause`, `campaign.budget_shift`.

## 7. Logistics Agent
- **Purpose**: Evaluates carrier performance across delivery corridors; automates SLA breach claim filing.
- **Formula**: `score = w1*cost + w2*eta + w3*reliability + w4*capacity`.
- **Proposed Actions**: `carrier.file_claim`, `shipment.expedite`.

## 8. Risk & Fraud Agent
- **Purpose**: Monitors transaction velocity, payment AVS/CVV matching, and unusual order sizes.
- **Proposed Actions**: `order.fraud_review`.

## 9. Analytics Agent
- **Purpose**: Synthesizes daily operational briefs and KPI variance rollups.
- **Proposed Actions**: Daily executive brief broadcasts.
