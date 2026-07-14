# Service Operations ERP MVP

## Product outcome

Enable a small service business to turn a client request into an assigned,
completed, costed, invoice-ready, and draft-invoiced work order without relying
on disconnected spreadsheets or unstructured closure notes.

## First vertical

Service operations with parts and projects. This includes field service,
maintenance, installation, and project-based service teams. The first vertical
uses generic field-service requirements; customer-specific terminology and
assumptions do not enter the cross-industry core.

## MVP workflow

1. Create or identify a customer and service location.
2. Open a work order from a request or quote.
3. Assign a technician and scheduled window.
4. Capture time, parts used, photos, and a structured closeout.
5. Validate closeout and route exceptions to an owner.
6. Mark the work order ready for invoice through the ERP workflow.
7. Draft one linked ERPNext Sales Invoice through a finance-triggered ERP
   action. The invoice remains a draft and does not update stock.
8. Draft a cited closeout summary through the AI control plane; require a
   human approval record. The initial policy is draft-only and cannot send or
   commit any ERP change.

## Reuse from ERPNext

- Customers, contacts, items, warehouses, projects, tasks, sales documents,
  invoices, users, roles, attachments, audit history, reports, and jobs.

## Custom MVP behavior

- Work-order state machine and structured closeout requirements.
- Technician time and parts capture tied to a work order.
- `Cannot Close` reason, named downstream owner, due date, and escalation.
- Idempotent draft Sales Invoice handoff from invoice-ready service work.
- Service profitability projection using bill rates and ERPNext Stock Entry
  costs, before labor overhead.
- Draft-only, cited AI closeout assistance with immutable audit and human review.

## Non-goals

- A new general ledger, tax engine, MRP engine, payroll engine, generic RAG
  chatbot, shared-row tenancy, autonomous financial posting, or Kubernetes.

## Acceptance metrics

- A technician can complete the workflow on a non-administrator account.
- Every time/part entry links to a work order and responsible user.
- A work order cannot become invoice-ready without required closeout data or a
  tracked exception.
- An Accounts user can draft exactly one linked Sales Invoice after manager-approved invoice readiness;
  the draft invoice does not submit or move stock.
- A work order displays projected revenue, issued-parts cost, and margin before
  labor overhead from deterministic ERP fields.
- An AI suggestion is traceable to its source inputs and cannot act without an
  authorized approval.
