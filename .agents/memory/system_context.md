# System Context & Architecture Overview

## Repository Map

- **Root Directory**: `/Users/mlvpatel/Downloads/ERP demo`
- **Primary Product Target**: Governed AI-native field-service ERP for maintenance, installation, and repair firms with 10 to 100 technicians.

## Key Component Responsibilities

1. **Upstream ERP Platform**:
   - ERPNext & Frappe Framework v15/v16.
   - Core ERP entities: Customer, Item, Warehouse, Sales Invoice, Stock Entry, Project, User.

2. **Custom Frappe Apps (`apps/`)**:
   - `ai_erp_core`: Cross-industry AI governance, `AI Proposal` & `AI Proposal Source` DocTypes, context uniqueness hashing, role permissions.
   - `ai_erp_service`: Field-service domain logic (`Service Work Order`, `Service Request`, `Service Location`, `Service Closure Exception`), profitability reporting, repair memory, deterministic scheduling scoring, evidence chain generation.
   - `ai_erp_distribution` & `ai_erp_manufacturing`: Configured demo stubs (`configured_demo`).

3. **Stateless AI Control Plane (`services/ai_control_plane/`)**:
   - FastAPI microservice implementing PII redaction, prompt rendering, live eval, OpenAI provider adapter, zero-cost `TemplateProvider` fallback.

4. **Contracts (`contracts/`)**:
   - `contracts/openapi/ai-control-plane-v1.yaml` (REST endpoints).
   - `contracts/events/service-operations-v1.yaml` (Async domain events).

5. **Infrastructure (`infra/`)**:
   - AWS Terraform IaC (`infra/aws/terraform/`), Docker Compose (`infra/compose/`), container runtime scripts (`infra/images/frappe/`).
