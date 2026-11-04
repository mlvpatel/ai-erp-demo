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
- The server method `ai_erp_service.evidence.get_evidence_chain` returns the
  replayable request-to-invoice chain for one work order. Every section is
  permission-scoped: related records go through standard list permissions, the
  finance section exists only for manager and accounts roles, and missing
  evidence is listed explicitly instead of being omitted. Section hashes and a
  chain hash make two replays of the same visible state comparable.
- The Evidence Replay button on the Service Work Order form renders that chain
  in a compact dialog: completeness, missing evidence, open exceptions, parts
  issued, AI proposal status, the compact ledger narrative stages, and, for
  manager and accounts roles only, the invoice handoff state with a link to the
  draft Sales Invoice. Finance handoff narrative stages appear only when the
  finance section is visible to the current role. When evidence is incomplete,
  the narrative headline states the gaps instead of implying a finished chain.
  The chronological timeline also includes closure exceptions and short
  proposal context-hash stubs, plus `policy_category` and token/duration when
  those audit fields were returned.
- The Evidence Packet button (service manager or accounts roles) exports the
  chain as a sanitized JSON file through
  `ai_erp_service.evidence.get_evidence_packet`: identifiers, hashes, statuses,
  citation hashes, `policy_category`, proposal `input_context_hash` idempotency
  rows (including token/duration when present), stock and invoice links, and
  unresolved exceptions only. Technicians cannot export. The export never
  contains draft text, prompts, provider responses, or attachment contents, and
  a synthetic packet is technical evidence, not human acceptance evidence.
  Concurrent identical `input_context_hash` requests reuse one proposal without
  a second provider call; AI Proposal approval remains review evidence only and
  does not create stock or invoice records.

Future connectors must use the versioned event shapes in
`contracts/events/service-operations-v1.yaml`. The current MVP does not publish
asynchronous events.

## Scheduling suggestions

The Suggest Technicians button on a draft or scheduled work order ranks
available technicians deterministically: prior completed work at the same asset
or location counts double, high SLA priority adds a bonus, skill/territory
matches add a bonus when those fields are set, open workload subtracts, and
ties break on workload and then on the technician id. Technicians with
overlapping scheduled work or missing required capability evidence are listed
as excluded with the reason. A missing schedule window aborts instead of
guessing availability.

Parts readiness follows the warehouse `issue_parts` would debit (each part
row `source_warehouse`, else the service location default). When that primary
bin is short, a technician whose `Service Technician Capability.van_warehouse`
holds enough stock can still rank as parts-ready (`parts_ready:van_stock`).
Van stock never posts Material Issue; managers still set part-row warehouses
before `issue_parts`.

Suggestions never assign anyone: the dispatcher applies a suggestion into the
form and the normal permission-checked save performs the assignment. Rejection
feedback is stored as work-order comments and shown as category counts in the
suggestion dialog; recording a rejection refreshes the rollup and never
auto-assigns or changes scores. Dispatchers can also call
`ai_erp_service.scheduling.suggestion_feedback_summary` for a bounded per-order
or site-wide category rollup.

A dispatcher can also request a draft explanation of the current ranking. The
explanation is stored as a cited, draft-only AI Proposal with no ERP side
effect: it always renders deterministically from the ranking facts (ADR-0009),
human review records the decision, and neither the draft nor its approval can
assign a technician.

## Repair memory drafts

On scheduled or in-progress work, the assigned technician or a service manager
can request Draft Repair Memory. The draft reorganizes cited, role-visible
prior work at the same asset or location: prior closeout notes become the
likely-fix section, parts used across prior visits are listed with occurrence
counts, and a failed or follow-up inspection in the history becomes a
missing-diagnostic warning. Customer alone is never a retrieval key. Only
supplied cited facts can appear, so the draft cannot invent parts. A requester
with no visible history, or with cited history that has no closeout notes,
parts, or follow-up inspection outcome, receives a stated abstention instead of
a suggestion. Contact-shaped and instruction-shaped free text in cited notes is
redacted or neutralized before it reaches the draft.

## Exception recovery drafts

On a Cannot Close work order with an open closure exception, a service manager
can request Draft Recovery Steps. Desk first shows the owned exception
(name, owner, due date, reason) and states that approving the draft cannot
close the work order. The proposal maps the exception reason to a
fixed recovery checklist, lists declared parts that are not yet issued, and
cites permission-scoped prior work at the same asset or location. Uncited prior
rows are dropped with an omission note. Instruction-like or contact-shaped free
text in cannot-close notes and cited history is sanitized before it reaches the
draft. An uncategorized reason with no visible history produces a stated
abstention. The draft cannot close the work order or resolve the exception; the
manager owns the recovery action and records the outcome through review.

## Margin leakage categories

The Service Profitability report classifies each work order with deterministic
margin-risk categories: missing billable time, discount / zero-rate labor,
missing part bill rate, part cost above bill rate, unknown cost basis, warranty
risk, failed inspection, unresolved exception, and repeat visit risk inside a
thirty-day window. Classification never invents a margin: missing cost data
becomes an unknown-cost category instead of a number. Each category carries
source evidence (hours, part items, neighbor work orders, open exceptions) into
the manager/finance evidence chain and packet.

Managers and finance users can open **Margin Leakage Summary** from a Service
Work Order. The dialog shows category counts, a capped high-risk queue (worst
margin first) with evidence snippets, and filters for risk category, status, and
creation date range. When the scan hits the 500-row page limit, or the high-risk
list hits its 50-row cap, the dialog states that counts or the queue may
understate the full set. The scan orders by newest creation first and only flags
truncation when more than the page limit exists. The profitability report uses
the same honesty rule at its 10,000-row bound and is visible to Accounts roles
as well as Service Managers. Technicians cannot call the summary API, open the
button, or run the report. The summary never changes billing records.

## Mobile field execution (online)

Technicians use the same Frappe Desk Service Work Order form on a phone-width
viewport. `public/css/mobile_field.css` enlarges primary actions, attach
controls, list rows, and child-table inputs to at least 44px, keeps sticky page
actions reachable, and keeps validation dialog copy readable. Playwright covers
the 390 by 844 path: assigned list, In Progress, time entry, parts declaration,
required inspection, closeout evidence upload, closeout submit, cannot-close
with an owned exception, and denial of finance, assignment, and manager-only
actions. Keyboard focus and accessible names are checked on status, inspection,
and cannot-close reason.

Offline IndexedDB drafts are not built, and no offline helper script is
registered in `app_include_js`, until field UAT asks for them. Online attachment failure or validation rejection
leaves the work order open with no stock or invoice side effect.

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

## Service operations and Frappe glossary

This glossary defines terms used across service workflows, custom Frappe apps, and ERPNext integration boundaries. Entity relationships are documented in [docs/architecture/domain-data-model.md](../architecture/domain-data-model.md) and container boundaries in [docs/architecture/system-boundaries.md](../architecture/system-boundaries.md).

| Term | Category | Definition and project context |
| --- | --- | --- |
| Service Work Order | Custom DocType | Core operational record in [apps/ai_erp_service](../../apps/ai_erp_service/README.md) tracking technician assignment, logged hours, declared parts, execution status, closeout validation, profitability, and linked draft invoices. |
| Service Request | Custom DocType | Intake document in [apps/ai_erp_service](../../apps/ai_erp_service/README.md) recording customer service inquiries, contact references, and site details prior to work order creation. |
| Service Location | Custom DocType | Customer site record in [apps/ai_erp_service](../../apps/ai_erp_service/README.md) linking an ERPNext Customer to physical address details and a default stock warehouse. |
| Service Closure Exception | Custom DocType | Blocker record tracking why an assigned work order cannot finish or become invoice-ready, including reason category, assigned owner, and target due date. |
| Service Technician Capability | Custom DocType | Operational profile in [apps/ai_erp_service](../../apps/ai_erp_service/README.md) recording skills, assigned territories, and optional van warehouse stock for dispatch ranking. |
| AI Proposal | Custom DocType | Immutable audit record in [apps/ai_erp_core](../../apps/ai_erp_core/README.md) storing draft AI output, model metadata, context hashes, and human review outcomes without transactional ERP write permissions. |
| AI Proposal Source | Custom Child Table | Citation row linked to an AI Proposal capturing source document names, source fields, and SHA-256 content hashes. |
| Evidence Chain | Architecture | Deterministic, role-scoped representation generated by `ai_erp_service.evidence.get_evidence_chain` capturing the request-to-invoice audit timeline, section hashes, and chain hash. |
| Evidence Packet | Architecture | Sanitized JSON export for service managers and accounts roles containing identifiers, timestamps, hashes, and links without raw prompt bodies or provider responses. |
| Context Hash | AI Governance | Normalized SHA-256 digest of input payload fields used by the AI control plane to enforce deterministic idempotency and prevent duplicate draft generation. |
| Cannot Close | Workflow State | Formal status indicating work order execution is blocked by missing parts, customer site refusal, safety hazards, or incomplete inspection. |
| Invoice Ready | Workflow State | Manager-verified milestone confirming that required labor hours, parts issue entries, inspection notes, and closeout evidence are complete before finance handoff. |
| DocType | Frappe Concept | Declarative model definition in the Frappe Framework defining database schema, controller logic, user interface layouts, and role permissions. |
| Child Table | Frappe Concept | Sub-table linked to a parent DocType row, such as Service Work Order Time or Service Work Order Part. |
| Bench | Frappe Concept | Command-line management environment and process runner managing Frappe sites, custom app installations, background workers, and database migrations. |
| Desk | Frappe Concept | Standard browser interface provided by Frappe for operational business users, managers, and desk agents. |
| Material Issue | ERPNext Concept | Stock Entry transaction type deducting issued parts inventory from a source warehouse to expense against a service job. |
| Sales Invoice | ERPNext Concept | Authoritative ERPNext financial ledger document recording customer receivables and revenue, generated strictly as an unposted draft by accounts roles. |
