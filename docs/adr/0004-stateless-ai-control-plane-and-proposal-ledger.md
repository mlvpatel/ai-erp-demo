# ADR-0004: Use a stateless AI control plane and an ERP-resident proposal ledger

- Status: Accepted
- Date: 2026-07-10
- Owners: AI ERP Demo

## Context

The first AI-assisted workflow needs a real runtime boundary, a durable audit
trail, source citations, and a human approval step. It must not introduce a
second transactional database or grant a model direct access to ERPNext/Frappe
records.

## Decision

Run a small, stateless `ai_control_plane` service outside Frappe. It accepts a
versioned, minimal closeout-summary request from one Frappe site, creates a
draft-only response, and does not connect to MariaDB, Redis, or ERPNext.

The Frappe site remains the system of record. `ai_erp_core` stores each response
as an immutable `AI Proposal` with its request ID, model/prompt metadata,
input/output hashes, citations, policy result, requester, reviewer, and review
timestamp. A site-scoped Frappe API creates the record only after validating the
control-plane response against `contracts/openapi/ai-control-plane-v1.yaml`.

The initial allowlist contains one action only: `service_closeout_summary`.
Its policy is `draft_only`; approval records the human decision but does not
write a work order, issue stock, create an invoice, send a message, or modify
any financial, inventory, payroll, access-control, or compliance record.

Each Frappe site calls the control plane with a shared service credential and
its site name as tenant scope. The service receives no database credentials and
keeps no persistence. A deterministic development renderer is permitted for
local demonstrations and must identify itself as such; a production model
adapter is a future configuration, not a hidden fallback.

## Consequences

- The demo has an executable AI boundary without a shadow ERP write path.
- Audit data is tenant-local because it lives in the relevant Frappe site.
- The control plane can later add model providers, retrieval, evaluation, and
  asynchronous jobs without changing the ERP proposal contract.
- AI output remains useful only after a person checks its citations and marks
  it approved or rejected.
- Sending reminders, applying generated text, or proposing transactional actions
  requires a separate typed contract, policy allowlist entry, ERP validator,
  approval flow, and tests.

## Alternatives considered

- Put model calls inside the Frappe custom app: rejected because it blurs the
  governed provider/prompt boundary required by ADR-0003.
- Give the control plane a database connection: rejected because it creates an
  unauditable ERP write path and a second tenant datastore.
- Add a generic chatbot first: rejected because it has no bounded business
  workflow, citation rule, or deterministic approval policy.
