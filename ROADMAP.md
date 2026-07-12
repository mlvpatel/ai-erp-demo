# Roadmap

AI ERP Demo grows by proving one safe workflow at a time. ERPNext/Frappe owns
the transactional ERP foundation; this repository adds industry packs,
governed AI proposals, contracts, and contributor-friendly automation.

## Now: local service-operations demo

Goal: make the first vertical workflow reproducible for contributors.

- Frappe/ERPNext development stack with pinned upstream commits.
- `ai_erp_core` shared AI proposal ledger.
- `ai_erp_service` service request, work order, technician closeout, parts,
  exception, invoice-readiness, and draft-invoice flow.
- Draft-only AI closeout proposal with citations, immutable audit, and human
  review.
- Demo seed command for synthetic service data.
- Static quality gates, contract tests, and service integration tests.

Exit gate:

- `scripts/dev.sh demo-check` passes on a prepared local stack.
- The root license decision is resolved before public release.
- A fresh clone can follow `docs/runbooks/local-demo.md`.

## Next: public alpha

Goal: make the repository safe and understandable for first external readers.

- Root `LICENSE` selected and generated app metadata reconciled.
- GitHub Actions green on the public repository.
- README has truthful quick-start and demo screenshots or a short GIF.
- First `good first issue` candidates are small documentation, fixture, or test
  improvements that do not touch money, stock, permissions, or AI approvals.
- Security, governance, support, contribution, and release docs are visible.

Exit gate:

- `scripts/check-open-source-ready.sh --release` passes.
- One maintainer is named in the public repository settings or governance docs.

## Later: AI-assisted execution with stricter controls

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

## Later: second and third industry packs

Goal: reuse the same safe pattern in broader industries.

Candidate order:

1. Distribution: sales order to pick/pack exception to delivery summary.
2. Light manufacturing: make-to-order quote to BOM/work-order availability
   exception.
3. Professional services: project kickoff to timesheet review to draft invoice.

Each pack must pass the entry and exit gates in
`docs/product/industry-pack-roadmap.md`.

## Not on the MVP roadmap

- Replacing ERPNext accounting, stock, tax, payroll, or permissions.
- A generic chatbot that bypasses typed ERP tools.
- Kubernetes, multi-region hosting, or advanced SSO before a real deployment
  requirement exists.
- Customer data, production backups, or private model prompts in the repository.
