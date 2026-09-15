# Estimated AWS Cost Model & Pricing Analysis

> **Disclaimer**: The following figures represent planning estimates based on standard AWS on-demand pricing in `us-east-1`. Workload specifics, token lengths, regional differences, and reserved capacity will affect actual invoices.

---

## 1. Small Production Workload Assumptions
- **Order Volume**: 100,000 orders/month.
- **Normalized Events**: 1,000,000 events/month.
- **Agent Invocations**: 200,000 invocations/month.
- **Token Assumptions**:
  - Complex reasoning (Supervisor, Support, Pricing): 2,500 input tokens, 500 output tokens.
  - Fast extraction / classification: 500 input tokens, 100 output tokens.
- **High Availability**: Multi-AZ deployment across 2 Availability Zones.

---

## 2. Itemized Monthly Cost Table

| AWS Service | Production Monthly Range (USD) | Development / Staging (USD) | Sizing & Optimization Notes |
|---|---|---|---|
| **ECS Fargate** (API, Web, Workers) | $250 – $700 | $60 – $180 | Auto-scaled based on SQS queue depth; 2 vCPU / 4 GB tasks. |
| **Aurora PostgreSQL Serverless v2** | $250 – $800 | $50 – $150 | Scales between 0.5 and 4 ACUs with automated backups & PITR. |
| **Amazon Bedrock** (Claude 3.5 & Titan) | $500 – $3,000 | $50 – $300 | Model routing: Haiku for classification, Sonnet for synthesis. |
| **ElastiCache Redis** | $80 – $250 | $15 – $40 | Cache for embeddings, idempotency locks, and sessions. |
| **EventBridge & SQS** | $10 – $80 | $2 – $10 | 1M custom events + DLQ retention. |
| **S3 & CloudFront** | $30 – $200 | $5 – $25 | Versioned knowledge base storage & static asset delivery. |
| **API Gateway, ALB & AWS WAF** | $80 – $300 | $20 – $60 | ALB with WAF rate limiting and bot control rules. |
| **VPC Endpoints & Data Transfer** | $100 – $500 | $15 – $50 | S3 Gateway Endpoint reduces NAT transfer costs significantly. |
| **CloudWatch, X-Ray & GuardDuty** | $100 – $500 | $20 – $80 | Application metrics, structured JSON logs, and X-Ray tracing. |
| **Cognito, KMS & Secrets Manager** | $20 – $150 | $5 – $20 | User authentication, automated secret rotation, and KMS keys. |
| **ESTIMATED TOTAL** | **$1,420 – $6,480 / mo** | **$238 – $915 / mo** | |

---

## 3. Cost Optimization Strategies
1. **Model Routing**: Route classification and routing tasks to fast, low-cost models (`Claude 3.5 Haiku`), reserving `Claude 3.5 Sonnet` for complex multi-constraint reasoning.
2. **Deterministic Arithmetic**: Never invoke an LLM for operations that can be calculated in Python/SQL.
3. **Gateway Endpoints**: Use free S3 Gateway Endpoints to avoid routing GBs of document chunks through costly NAT Gateways.
4. **Scheduled Shutdown**: Non-production environments can scale to zero outside business hours, saving 60-70% of dev compute costs.
5. **Compute Savings Plans**: Commit to 1-year or 3-year Compute Savings Plans once workload baseline stabilizes for 25–40% discounts on Fargate.
