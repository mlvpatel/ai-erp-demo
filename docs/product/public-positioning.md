# Public positioning

## One-line description

AI ERP Demo is an open-source, AI-assisted ERP starter built on ERPNext/Frappe,
starting with a service-operations industry workflow and strict human approval
for consequential actions.

## Short description

The project is not a new generic ERP core. It reuses ERPNext/Frappe for
accounting, stock, users, permissions, workflows, reports, and audit history,
then adds custom industry packs and a governed AI control plane. The first
vertical turns a service request into an assigned, completed, costed,
invoice-ready, and draft-invoiced work order.

## Target users

- Small service, maintenance, installation, or field-operations teams that have
  outgrown spreadsheets.
- Developers who want to build ERPNext/Frappe industry packs without patching
  upstream source.
- Founders exploring AI-assisted ERP workflows where AI proposes and people
  approve.

## Differentiation

- ERP correctness first: Frappe/ERPNext stays the source of truth for money,
  stock, users, roles, and workflow.
- Vertical-first: one complete service-operations workflow before adding more
  industries.
- AI with guardrails: AI drafts, explains, classifies, retrieves, and proposes;
  it does not directly post stock, financial, payroll, permission, or compliance
  changes.
- Open-source-ready structure: ADRs, contracts, security docs, publication
  runbooks, issue templates, quality gates, and synthetic fixtures.
- Network copyleft: repository-owned code is licensed under
  `AGPL-3.0-only`; upstream dependencies retain their own licenses.

## Demo story

1. A customer has a service need at a location.
2. A service request creates a linked service work order.
3. A technician records time, parts, and closeout notes.
4. The workflow blocks invoice-readiness until required closeout data or a
   tracked exception exists.
5. A manager reviews the work and marks it invoice-ready; a separately
   authorized Accounts user creates exactly one linked draft Sales Invoice.
6. The AI control plane drafts a cited closeout summary for human review.

## Claims to avoid before public release

- Do not claim this is production-ready.
- Do not claim autonomous ERP posting or autonomous customer messaging.
- Do not claim broad all-industry coverage; the architecture supports industry
  packs, but the implemented proof is service operations.

## Suggested GitHub topics after licensing

`erpnext`, `frappe`, `erp`, `ai`, `field-service`, `service-management`,
`open-source`, `workflow`, `human-in-the-loop`
