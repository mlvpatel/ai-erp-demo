---
name: system-architecture-and-design
description: System architecture guidelines, ADR authoring, C4 boundary modeling, domain data models, and API contract design.
---

# System Architecture & Design Skill

## Purpose
Governs system architecture evolution, Architecture Decision Record (ADR) authoring, C4 container boundaries, domain data modeling, and API contract specifications.

## Key Principles & Playbooks

1. **Architecture Decision Records (ADRs)**:
   - Before adding any new service, datastore, third-party provider, major dependency, or structural change, author an ADR in `docs/adr/` using `docs/adr/0000-template.md`.
   - Ensure clear Decision, Context, Consequences, and Security/Privacy impacts are documented.

2. **Domain Data Modeling**:
   - Primary custom entities reside in `apps/ai_erp_service` (`Service Work Order`, `Service Request`, `Service Location`, `Service Closure Exception`).
   - Cross-industry governance entities reside in `apps/ai_erp_core` (`AI Proposal`, `AI Proposal Source`).
   - Document domain data model changes in `docs/architecture/domain-data-model.md`.

3. **API & Event Contract Specification**:
   - REST/HTTP contracts for the AI control plane are defined in `contracts/openapi/ai-control-plane-v1.yaml`.
   - Asynchronous domain events are specified in `contracts/events/service-operations-v1.yaml`.
   - Update `contracts/catalog.json` when adding or modifying contracts and verify via `scripts/check-contract-catalog.py`.
