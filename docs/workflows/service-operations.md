# Service operations workflow

## Roles

- Service Dispatcher schedules work.
- Service Technician records time, parts, closeout notes, and evidence.
- Service Manager closes work, issues parts, and marks work invoice-ready.
- Accounts User drafts the linked Sales Invoice after invoice readiness.
- AI Proposal Approver reviews AI drafts without changing ERP state.

## Happy path

1. Create a Service Request for an ERPNext Customer and optional Service
   Location.
2. Create the linked Service Work Order.
3. A dispatcher or manager records manager-controlled service foundation data:
   Service Asset, Service Priority, SLA Due At, Warranty Status, and whether an
   inspection is required.
4. Schedule the work order and assign one technician.
5. The assigned technician moves it to In Progress, records their own time,
   declares parts, records any required inspection result and notes, attaches
   closeout evidence, and submits closeout.
6. A manager issues declared parts. The app creates one submitted ERPNext
   Material Issue and links it to each part row.
7. A manager closes the work order and marks it Invoice Ready.
8. An Accounts User or Accounts Manager with ERPNext Sales Invoice create permission drafts the linked
   Sales Invoice. The action is idempotent, creates only a draft, and does not
   update stock.
9. A technician or manager may request a Draft AI Closeout Summary. The AI
   proposal is cited, immutable, and review-only; approval has no invoice,
   stock, status, payroll, access, or email side effect.

## Audit evidence

- AI Proposal records preserve source hashes, request metadata, model metadata,
  immutable draft content, and human review evidence.
- The evidence chain starts from the Service Work Order and returns to it:
  Stock Entry identifiers are stored on Service Work Order part rows, and
  Sales Invoice identifiers are stored on the Service Work Order.
- AI Proposal approval or rejection is audit evidence only; deterministic
  manager actions create or link ERP transaction records.

Future connectors must use the versioned event shapes in
`contracts/events/service-operations-v1.yaml`. The current MVP does not publish
asynchronous events.

## Billing controls

- Labor invoicing requires a non-stock Labor Billing Item and Hourly Rate.
- Fractional labor hours require a labor item UOM that allows fractions.
- Each part line requires a Bill Rate before invoice drafting.
- All declared parts must already have a Stock Entry before close or invoice
  drafting.
- After a Sales Invoice is linked, the billing basis is immutable on the work
  order.

## Service foundation controls

- Service Asset, Service Priority, SLA Due At, Warranty Status, and Inspection
  Required are manager-controlled fields.
- Technicians can read those fields on assigned work but cannot change them.
- In Warranty work requires a linked Service Asset.
- If Inspection Required is set, a technician must record an Inspection Result
  before closeout. Failed or follow-up inspection results require Inspection
  Notes.

## Profitability projection

- Projected Revenue is calculated from labor hours multiplied by Hourly Rate,
  plus part quantities multiplied by Bill Rate.
- Issued Parts Cost is calculated from submitted ERPNext Stock Entry Detail
  amounts linked to the work order parts.
- Projected Margin is before labor overhead. Add employee costing only after
  the project adopts ERPNext Timesheet/HR cost sources.
