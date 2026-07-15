# Roadmap

AI ERP Demo grows by proving one safe workflow at a time. ERPNext/Frappe owns
the transactional ERP foundation; this repository adds industry packs,
governed AI proposals, contracts, and contributor-friendly automation.

## Now: zero-cost local synthetic demo

Goal: publish a reproducible private demo that runs on a maintainer's computer
without AWS, a hosted model, or billable provider credentials.

- Frappe/ERPNext development stack with pinned upstream commits.
- `ai_erp_core` shared AI proposal ledger.
- `ai_erp_service` service request, work order, technician closeout, parts,
  exception, invoice-readiness, and draft-invoice flow.
- Draft-only AI closeout proposal with citations, immutable audit, and human
  review.
- Demo seed command for synthetic service data.
- Technician field-level restrictions, scoped related-record reads, finance-role
  separation, overdue escalation, and negative authorization tests.
- Governed OpenAI adapter with strict schemas, redaction, per-site limits,
  serialization, `/readyz`, safe audit metadata, and pre-activation evaluation.
- UI-driven role journeys, configured-demo evidence, and static, contract,
  integration, browser, infrastructure, and image-security gates.
- Deterministic `template` AI provider for a reliable, draft-only demonstration;
  it demonstrates governance, not hosted-model quality.

Exit gate:

- A clean checkout completes the static and Docker-backed demo gates.
- Three synthetic-only screenshots show technician execution, manager/finance
  handoff, and the cited draft-only AI proposal.
- The private GitHub pull request has current evidence and green checks.
- No production, UAT, legal-compliance, capacity, recovery, or all-industry claim
  is made.

## Deferred: approved field-service production pilot

Goal: operate a small field-service pilot within the documented USD 600 target
and accepted single-NAT/single-Valkey availability limits.

- Activate only after secrets, domain/certificate, budget review, live evaluation,
  migrations, and authenticated smoke checks pass.
- Monitor queue age, database capacity, EFS, AI latency/rate/cost, permission
  failures, backups, restores, and deployment rollbacks.
- Collect design-partner and human UAT evidence separately from automation.
- Run immutable-image, exact-capacity, recovery, deletion, and rollback gates
  only after credentials, budget, domain, and accountable owners are approved.

Exit gate:

- `automated_complete`, `deployment_evidence_complete`, and `pilot_approved`
  are set only when their separate evidence exists.
- A named support owner accepts the pilot runbooks and escalation path.

## Later: additional governed AI proposals

Goal: expand from draft-only AI summaries to approved operational proposals.

- Add one AI proposal type at a time, such as overdue-invoice reminder draft,
  work-order exception explanation, or purchasing exception summary.
- Version every AI-facing tool contract under `contracts/`.
- Add regression tests proving AI output cannot directly post financial, stock,
  payroll, access-control, or compliance changes.
- Record model, prompt version, source inputs, policy result, human approver,
  and final ERP outcome.

Exit gate:

- A non-admin user can complete the workflow with correct permissions.
- The same proposal can be replayed or rejected without duplicate ERP writes.

## Later: promote configured demos only after validation

Goal: reuse the same safe pattern in broader industries.

Candidate order:

1. Distribution currently remains `configured_demo`: draft Sales Order to Pick
   List, shortage review, and draft Delivery Note using standard ERPNext only.
2. Light manufacturing remains `configured_demo`: demand to BOM, production
   planning/work order, shortage, and draft Material Request using ERPNext only.
3. Professional services: project kickoff to timesheet review to draft invoice.

Each pack must pass the entry and exit gates in
`docs/product/industry-pack-roadmap.md`.

## Not on the MVP roadmap

- Replacing ERPNext accounting, stock, tax, payroll, or permissions.
- A generic chatbot that bypasses typed ERP tools.
- Kubernetes, multi-region hosting, or advanced SSO before a validated pilot
  requirement exists.
- Customer data, production backups, or private model prompts in the repository.
