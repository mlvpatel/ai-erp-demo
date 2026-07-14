# Industry pack roadmap

AI ERP Demo should grow by proving one industry workflow at a time, not by
creating a generic feature pile. ERPNext/Frappe remains the core platform; each
industry pack should add only the workflow, documents, permissions, fixtures,
contracts, and AI proposals that the base ERP cannot express cleanly.

## Sequencing principle

1. Reuse ERPNext modules and configuration first.
2. Add custom DocTypes/workflows only for verified industry gaps.
3. Keep AI as retrieval, classification, drafting, explanation, or exception
   support.
4. Require deterministic ERP validation and authorized approval for every
   financial, stock, payroll, permission, or compliance mutation.
5. Ship one end-to-end demo workflow before widening the pack.

## Candidate packs

The same sequence is tracked in `config/industry-packs.json` and validated by
`scripts/check-industry-pack-manifest.py`. Status transitions are governed by
`docs/workflows/industry-pack-lifecycle.md` and validated by
`scripts/check-industry-pack-lifecycle.py`. Update the table, manifest, and
lifecycle evidence when a pack changes status.

| Order | Pack | Why it fits | First proof workflow | Reuse first |
| --- | --- | --- | --- | --- |
| 1 | Field service | Clear fit for the current service, parts, technician, and invoice-ready flow. | Request to work order to parts issue to manager review to draft invoice. | CRM, Stock, Selling, Accounting |
| 2 | Distribution | Broad industry reach, strong ERPNext stock/selling/buying foundation, and clear AI opportunities in exceptions. | Sales order to pick/pack issue to delivery exception summary. | Stock, Selling, Buying, Accounting |
| 3 | Light manufacturing | Common ERP buyer need; ERPNext already has BOMs, work orders, and stock movements. | Make-to-order quote to BOM/work order to material availability exception. | Manufacturing, Stock, Selling |
| 4 | Professional services | Lower inventory risk and useful AI drafting for statements of work, time summaries, and billing review. | Project kickoff to timesheet review to draft invoice. | Projects, Selling, Accounting |
| 5 | Maintenance/assets | Close to field service, but asset history and preventive schedules become the proof point. | Preventive schedule to service work order to asset maintenance history. | Assets, Maintenance, Stock |

## Entry gate for a new pack

Distribution and light manufacturing have explicit hypothesis briefs under
`docs/discovery/`. They remain reserved with entry gate `not_started` until a
named design partner supplies human validation; the briefs are not approval to
generate Frappe application code.

A pack is ready for implementation only when it has:

- A named target user and business job.
- One demo workflow with start and finish states.
- A decision on which ERPNext modules are reused unchanged.
- A short list of custom behavior that cannot be represented by configuration.
- Synthetic fixtures with no customer data.
- Permission and approval rules.
- Tests for the business rules and the highest-risk transaction boundary.

Use `industry-pack-design-template.md` to capture this evidence before adding
new generated Frappe app code.

## Exit gate for a demo-quality pack

A pack is demo-quality only when:

- A fresh local site can install it with documented commands.
- The first workflow passes an integration test.
- The README explains the workflow in business language.
- AI proposals are auditable and draft-only.
- No workflow depends on editing upstream Frappe/ERPNext source.
