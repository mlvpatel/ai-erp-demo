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
  proposal context-hash stubs for replay comparison.
- The Evidence Packet button (service manager or accounts roles) exports the
  chain as a sanitized JSON file through
  `ai_erp_service.evidence.get_evidence_packet`: identifiers, hashes, statuses,
  citation ids, proposal `input_context_hash` idempotency rows, stock and
  invoice links, and unresolved exceptions only. Technicians cannot export.
  The export never contains draft text, prompts, provider responses, or
  attachment contents, and a synthetic packet is technical evidence, not human
  acceptance evidence.

Future connectors must use the versioned event shapes in
`contracts/events/service-operations-v1.yaml`. The current MVP does not publish
asynchronous events.

## Scheduling suggestions

The Suggest Technicians button on a draft or scheduled work order ranks
available technicians deterministically: prior completed work at the same asset
or location counts double, open workload subtracts, and ties break on workload
and then on the technician id. Technicians with overlapping scheduled work are
listed as excluded with the reason. A missing schedule window aborts instead of
guessing availability. Suggestions never assign anyone: the dispatcher applies
a suggestion into the form and the normal permission-checked save performs the
assignment. Rejection feedback is stored as work-order comments and shown as
category counts in the suggestion dialog; it never auto-assigns or changes
scores by itself. Dispatchers can also call
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
missing-diagnostic warning. Only supplied cited facts can appear, so the draft
cannot invent parts, and a requester with no visible history receives a stated
abstention instead of a suggestion.

## Exception recovery drafts

On a Cannot Close work order with an open closure exception, a service manager
can request Draft Recovery Steps. The proposal maps the exception reason to a
fixed recovery checklist, lists declared parts that are not yet issued, and
cites permission-scoped prior work at the same asset or location. Uncited prior
rows are dropped with an omission note. Instruction-like or contact-shaped free
text in cannot-close notes and cited history is sanitized before it reaches the
draft. An uncategorized reason with no visible history produces a stated
abstention. The draft cannot close the work order or resolve the exception; the
manager owns the recovery action and records the outcome through review.

## Margin leakage categories

The Service Profitability report classifies each work order with deterministic
margin-risk categories: missing billable time, zero-rate labor, missing part
bill rate, part cost above bill rate, unknown cost basis, warranty risk, failed
inspection, unresolved exception, and repeat visit risk inside a thirty-day
window. Classification never invents a margin: missing cost data becomes an
unknown-cost category instead of a number.

Managers and finance users can open **Margin Leakage Summary** from a Service
Work Order. The dialog shows category counts, a capped high-risk queue (worst
margin first), and an optional single-category filter. When the scan hits the
500-row page limit, or the high-risk list hits its 50-row cap, the dialog states
that counts or the queue may understate the full set. The scan orders by newest
creation first and only flags truncation when more than the page limit exists.
Technicians cannot call the summary API or see the button. The summary never
changes billing records.

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
