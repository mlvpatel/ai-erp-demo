# ADR-0001: Adopt ERPNext/Frappe as the MVP ERP core

- Status: Accepted
- Date: 2026-07-10
- Owners: AI ERP Demo

## Context

The product needs trustworthy accounting, inventory, roles, workflows, and
auditable business records. Building those primitives from scratch in a
greenfield FastAPI stack would delay the service-operations MVP and create
unnecessary financial and migration risk.

## Decision

Use matching Frappe and ERPNext v16 branches as upstream dependencies. Build
all product behavior as custom Frappe apps; do not patch or vendor upstream
source. Reuse ERPNext records and workflows before creating new DocTypes.

The custom product boundary is:

- `ai_erp_core`: cross-industry policy, audit helpers, and shared extensions.
- `ai_erp_service`: service work orders, technician closeout, time, and parts.
- `ai_erp_connectors`: replaceable external-system adapters.
- `ai_control_plane`: AI orchestration outside the transactional ERP write path.

## Consequences

- ERP accounting, inventory, roles, APIs, jobs, and UI capabilities remain
  upstream-owned rather than being rebuilt.
- Developers must learn Frappe conventions and test upgrades against custom
  apps.
- The MVP can focus on service-operations differentiation and auditable AI.

## Alternatives considered

- Greenfield FastAPI/Next.js ERP: rejected for MVP because it recreates core
  accounting, inventory, workflow, and localisation responsibilities.
- Odoo Community: viable later comparison, but not selected for the initial
  technical spike because the project already chose Frappe custom-app boundaries.
