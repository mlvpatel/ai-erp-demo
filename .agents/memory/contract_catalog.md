# Contract Catalog Memory

## Active Contracts

1. **AI Control Plane OpenAPI Spec**:
   - **Path**: `contracts/openapi/ai-control-plane-v1.yaml`
   - **Version**: 1.0.0
   - **Endpoints**:
     - `GET /healthz` - Process liveness
     - `GET /readyz` - Provider readiness
     - `POST /api/v1/proposals/generate` - Stateless proposal generation with PII redaction and citation enforcement.

2. **Service Operations Event Spec**:
   - **Path**: `contracts/events/service-operations-v1.yaml`
   - **Version**: 1.0.0
   - **Domain Events**:
     - `service_request.created`
     - `work_order.assigned`
     - `work_order.parts_issued`
     - `work_order.closed`
     - `work_order.exception_raised`
     - `sales_invoice.drafted`

## Catalog Registry Config
- **Path**: `contracts/catalog.json`
- **Validation Script**: `scripts/check-contract-catalog.py`
