# AI-Powered Autonomous E-Commerce Operations Platform

[![Status](https://img.shields.io/badge/Status-Operational-success)](http://localhost:8000)
[![Target Cloud](https://img.shields.io/badge/Cloud-AWS-orange)](infra/)
[![Models](https://img.shields.io/badge/AI-Amazon%20Bedrock%20%7C%20Claude%203.5-blue)](brain/)
[![Architecture](https://img.shields.io/badge/Architecture-Event--Driven%20Multi--Agent-purple)](docs/architecture.md)

An enterprise-grade, event-driven multi-agent platform designed to automate end-to-end retail operations across **Inventory**, **Order Operations**, **Customer Support**, **Dynamic Pricing**, **Marketing Campaigns**, **Logistics**, **Fraud/Risk**, and **Analytics**.

---

## 🌟 Key Capabilities
1. **Multi-Agent Orchestration**: A central Supervisor agent coordinates 8 specialist agents over an asynchronous event mesh.
2. **Separated Reasoning & Execution**: LLMs emit typed JSON proposals that must pass through deterministic policy validation before execution.
3. **Human-in-the-Loop (HITL)**: Risky or monetary actions require explicit human operator approval through the Operations Inbox.
4. **Deterministic Arithmetic**: Safety stock, lead-time demand, contribution margin, and carrier scorecards are computed in code, preventing hallucinations.
5. **Grounded Support RAG Desk**: Support tickets are triaged with live carrier telemetry and policy document citations.
6. **Full Observability & Audit Trail**: Every run records prompt version, retrieved citations, risk score, approver identity, and execution reference.

---

## 📂 Repository Structure

```
├── apps/
│   ├── api/                     # FastAPI control plane & commerce REST API
│   └── web/                     # React / Vite operations dashboard (glassmorphic UI)
├── brain/                       # Cognitive multi-agent engine
│   ├── supervisor/              # Event routing matrix & parallel graph runner
│   ├── inventory/               # Lead-time demand & safety-stock formulas
│   ├── orders/                  # Fulfillment SLA & exception handling
│   ├── support/                 # Grounded RAG response drafting
│   ├── pricing/                 # Contribution margin optimizer
│   ├── marketing/               # Ad budget leakage protection
│   ├── logistics/               # Carrier scoring & transit delay claims
│   ├── risk/                    # Fraud & transaction anomaly scoring
│   ├── analytics/               # Daily executive briefings & KPI rollups
│   └── shared/                  # Policy engine, contracts & model gateway
├── infra/                       # AWS CDK v2 TypeScript infrastructure stacks
│   ├── lib/network-stack.ts     # Multi-AZ VPC, subnets, VPC endpoints
│   ├── lib/data-stack.ts        # Aurora Serverless v2 PostgreSQL, S3, KMS
│   ├── lib/compute-stack.ts     # ECS Fargate, EventBridge, SQS with DLQ
│   └── lib/edge-stack.ts        # ALB, CloudFront, Cognito User Pool
├── docs/                        # Complete project documentation & deliverables
│   ├── presentation.html        # Interactive 12-slide presentation deck
│   ├── presentation.md          # Presentation deck source in Markdown
│   ├── architecture.md          # Cloud architecture specification & C4 diagrams
│   ├── costing.md               # Detailed AWS monthly cost model
│   └── agent-cards.md           # Agent specifications, triggers & tool schemas
├── scripts/
│   └── seed_demo.py             # Section 24 scenario seeder (SKU RUN-SHOE-BLK-42)
├── tests/                       # Automated unit and policy engine tests
├── docker-compose.yml           # Local multi-container deployment
└── run_platform.bat             # Single-click launcher for Windows
```

---

## 🚀 Quickstart (Local Run)

### 1. Seed Demo Data & Execute Section 24 Scenario
```bash
python scripts/seed_demo.py
```

### 2. Launch the Control Plane & Web Dashboard
```bash
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```
- Open **`http://localhost:8000`** to access the live Operations Dashboard.
- Open **`http://localhost:8000/docs`** to inspect the interactive OpenAPI Swagger documentation.

Alternatively, on Windows, double-click **`run_platform.bat`**.

---

## 🧪 Section 24 Demo Scenario Walkthrough

The platform includes a pre-packaged simulation of the end-to-end incident from Section 24 of the blueprint:

1. **Incident Trigger**:
   - SKU `RUN-SHOE-BLK-42` (Apex Vapor Running Shoe) has only 15 net available units with 10 units/day demand (**1.5 days of cover remaining**).
   - An active Google Ads campaign is burning **$250.00/day** promoting this SKU.
   - Order #10045 containing this shoe is stuck in a regional sorting facility for 48 hours.
   - Customer ticket #401 asks where the order is.
2. **Multi-Agent Concurrent Reaction**:
   - **Inventory Agent**: Proposes a replenishment PO of 440 units ($18,480) with supplier lead-time constraints.
   - **Marketing Agent**: Proposes pausing the ad campaign to prevent ad budget waste on an out-of-stock item.
   - **Pricing Agent**: Proposes a 5% price increase to dampen velocity and lift contribution margin.
   - **Support Agent**: Drafts a verified reply citing the carrier sorting scan without hallucinating delivery dates.
3. **Approval & Execution**:
   - Operator reviews proposals in the **Approvals Inbox** (`http://localhost:8000`).
   - One-click approval records the operator's identity, dispatches the action to the executor, and creates an immutable audit log entry.

---

## 📊 Deliverables Index

| Deliverable | Location | Description |
|---|---|---|
| **Operations Dashboard** | [apps/web/](apps/web/) | React glassmorphic command center with KPI metrics & approval inbox. |
| **Interactive Presentation** | [docs/presentation.html](docs/presentation.html) | 12-slide interactive presentation deck for stakeholders and pitches. |
| **Presentation Source** | [docs/presentation.md](docs/presentation.md) | Slide-by-slide copy and narrative in Markdown format. |
| **Cloud Architecture** | [docs/architecture.md](docs/architecture.md) | EventBridge, ECS Fargate, Bedrock, and Aurora architecture specs. |
| **Itemized Costing** | [docs/costing.md](docs/costing.md) | $1,420–$6,480/mo (Prod) and $238–$915/mo (Dev) cost model. |
| **Agent Cards** | [docs/agent-cards.md](docs/agent-cards.md) | Triggers, deterministic math formulas, and safety rules for each agent. |
| **AWS CDK Stacks** | [infra/lib/](infra/lib/) | TypeScript CDK v2 definitions for Network, Data, Compute, and Edge. |
| **Unit Test Suite** | [tests/test_platform.py](tests/test_platform.py) | Unit tests verifying deterministic formulas, policy engine, and routing. |
