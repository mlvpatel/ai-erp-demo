# Demo script

Use this script when recording a README screenshot, GIF, maintainer walkthrough,
or first public demo issue. Demo claim: service operations MVP, not
production-ready ERP for all industries.

The demo should show one coherent path: service request, service work order,
technician closeout, manager stock issue, invoice-ready review, draft invoice,
and a cited AI closeout proposal that stays review-only.

## Before recording

Run the local demo setup from [local-demo.md](local-demo.md), then confirm the
safe demo state:

```sh
scripts/dev.sh demo-info
scripts/dev.sh seed-demo
scripts/dev.sh demo-check
```

Use only synthetic records. Do not record customer data, credentials, private
prompts, local-only secrets, production exports, or real attachments. Do not
show `development/.env`, terminal output that contains passwords, API tokens,
or private browser state. Hide or crop local passwords and blur browser
extensions and local usernames if needed. Do not claim production readiness,
autonomous posting, or complete support for all industries.

## Story beats

### Act 1 — Intake and schedule

Show the Service Request created by the synthetic seed and the linked draft
Service Work Order. The point is that the first vertical is concrete field
service, not a generic dashboard shell.

Evidence claim: `technician-non-admin-workflow`.

### Act 2 — Technician closeout

Show the assigned technician scope, time entries, declared parts, closeout
notes, and closeout evidence path. The technician can work in their allowed
scope, while final close and invoice-ready actions remain manager-only.

Evidence claims: `technician-non-admin-workflow`,
`time-and-parts-responsibility`, and `invoice-readiness-closeout-gate`.

### Act 3 — Manager and finance transaction controls

Show the manager-issued submitted ERPNext Material Issue linked on the Service
Work Order part rows. The manager marks the work invoice-ready, then a separately
authenticated Accounts user creates the linked draft Sales Invoice. Make clear
that the invoice is draft-only and does not update stock.

Evidence claims: `time-and-parts-responsibility`,
`finance-draft-invoice-idempotent`, and `profitability-projection`.

### Act 4 — AI closeout proposal

Show the AI Proposal record for the work order. It must show cited source rows,
source hashes, model metadata, prompt version, draft content, requested_by, and
human review fields. Explain that AI Proposal approval records review evidence
only; it does not post invoices, stock, payroll, permissions, compliance
changes, status changes, or emails.

Evidence claim: `ai-proposal-traceable-human-approved`.

### Act 5 — Safety and extensibility

Close with the repository evidence: ERPNext/Frappe stays upstream, custom code
lives in `apps/`, AI orchestration lives in `services/ai_control_plane/`,
contracts live in `contracts/`, and public claims are gated by static checks.
Mention that future industry packs are planned through the industry-pack
lifecycle, not claimed as implemented.

Evidence claims: `ai-proposal-traceable-human-approved` and
`finance-draft-invoice-idempotent`.

## Suggested README media

The zero-cost local demo release includes these three synthetic screenshots:

1. `docs/media/demo/service-work-order-execution.jpg`: Service Work Order with
   technician closeout and declared parts.
2. `docs/media/demo/manager-finance-handoff.jpg`: linked Stock Entry and draft
   Sales Invoice evidence under the Accounts role.
3. `docs/media/demo/ai-proposal-draft-only.jpg`: AI Proposal with cited sources,
   human review, and the `Draft Only` policy.

Replace these files only after the same clean synthetic walkthrough passes.
Never edit a screenshot to hide a workflow defect or permission failure.

Keep captions factual:

- "Service-operations MVP on ERPNext/Frappe."
- "Manager-gated stock issue and finance-gated draft invoice."
- "AI drafts are cited, immutable, and review-only."

Do not include screenshots until `scripts/dev.sh demo-check` passes on the same
checkout used for recording.
