# Service operations interview guide

Use this guide to validate the first vertical without importing customer data
into the repository. Capture only anonymised notes, screenshots with sensitive
fields removed, and synthetic examples.

## Session goals

- Confirm the service request to invoice-ready workflow.
- Identify required closeout data and invoice blockers.
- Separate ERPNext configuration from custom app behavior.
- Find AI drafting or exception-summary use cases that are useful but safe.
- Validate roles, approvals, and audit requirements.

## Participants

Interview at least one person from each role when possible:

- Dispatcher or coordinator.
- Technician or field worker.
- Service manager or operations owner.
- Finance/accounting user.
- Business owner or general manager.

## Questions by workflow stage

### Intake and scheduling

- Where does a service request start: phone, email, quote, portal, recurring
  schedule, or internal task?
- Which customer, site, asset, contact, and priority fields are required before
  scheduling?
- What information is often missing or wrong at intake?
- Who is allowed to assign or reassign a technician?

### Technician execution

- What does the technician need before going on site?
- Which time, parts, photos, notes, measurements, or signatures are mandatory?
- What can the technician decide alone, and what requires manager approval?
- What are the common reasons a job cannot be closed?

### Parts and inventory

- Are parts planned before the visit, declared after the visit, or both?
- Who is authorized to post stock movement?
- How are returns, substitutions, warranty parts, and unplanned parts handled?
- What duplicate or late stock-posting mistakes happen today?

### Closeout and billing

- What makes a work order ready for billing?
- Which closeout fields must appear on an invoice or customer report?
- Which invoice lines are deterministic from time and parts?
- Which charges need manager or finance judgment?
- What should block invoice drafting?

### AI assistance

- Which text is repetitive enough for AI to draft: closeout summary, customer
  update, exception explanation, invoice note, or internal handoff?
- What sources should AI cite?
- What should AI never send, approve, post, or change?
- Who must review the AI output before it affects a customer or ERP record?

## Evidence to capture

- Current-state workflow map.
- Target-state workflow map.
- Role and permission matrix.
- Required closeout checklist.
- Billing blocker list.
- ERPNext reuse map.
- Custom behavior gap list.
- Synthetic fixture examples.
- Acceptance criteria for one demo workflow.

## Red flags

Stop and escalate design review if discovery reveals:

- The workflow changes taxes, payroll, regulated compliance, or customer credit.
- Multiple legal entities or tenants must share a database.
- AI is expected to post invoices, stock entries, payroll, permissions, or
  compliance decisions directly.
- Real customer exports or private attachments are needed to reproduce the
  workflow.

## Design handoff

Before implementation, update:

- `docs/product/mvp-scope.md`
- `docs/workflows/service-operations.md`
- `docs/security/threat-model.md`
- affected ADRs if the architecture or dependencies change
- tests for the highest-risk permission, idempotency, and transaction boundary
