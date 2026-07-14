# Discovery to design plan

The product goal is an AI-assisted ERP that can grow across industries without
becoming a vague "ERP for everyone." The discovery plan therefore starts with
one working vertical, extracts reusable patterns, and only then adds the next
industry pack.

## Phase 1: Foundation decision

Status: mostly complete for MVP.

- Select ERP platform and record why.
- Define extension boundaries for custom apps, AI service, contracts, tests,
  infrastructure, and documentation.
- Decide the first vertical workflow.
- Record AI safety policy: AI can draft, classify, summarize, and propose; ERP
  validation plus authorized users perform business mutations.

Evidence in this repo:

- `docs/adr/0001-adopt-erpnext-frappe-core.md`
- `docs/architecture/tech-stack-2026-07.md`
- `docs/discovery/open-source-erp-scan-2026-07.md`

## Phase 2: First vertical discovery

Target vertical: service operations with parts, technician work, closeout,
exceptions, and invoice readiness.

Questions to answer:

- Who creates the request?
- Who schedules or assigns the technician?
- What closeout information is mandatory before billing?
- Which exceptions block invoice readiness?
- Which parts transactions must be posted, and by whom?
- Which invoice lines are deterministic, and which require manager judgment?
- Which AI drafts are useful but safe?

Outputs:

- Persona notes for technician, service manager, finance user, and owner.
- Current-state workflow map.
- Target-state workflow map.
- Required ERPNext reuse list.
- Custom DocType/workflow gap list.
- Permission matrix.
- Synthetic test fixture plan.

## Phase 3: Design the MVP workflow

Convert discovery into a clickable and testable ERP workflow:

1. Service Request
2. Service Work Order
3. Technician time and parts
4. Cannot Close exception
5. Manager closeout review
6. Parts issue
7. Invoice readiness
8. Draft Sales Invoice
9. Draft AI closeout summary with human review

Design artifacts:

- Workflow state table.
- Required fields by role/state.
- User stories and acceptance criteria.
- AI proposal policy table.
- Test matrix for permissions, idempotency, and blocked states.

## Phase 4: Validate with one design partner

Use a representative field-service design-partner shape without hardcoding
customer-specific business names into the cross-industry core.

Validation sessions:

- Technician workflow walkthrough.
- Manager exception and invoice-readiness walkthrough.
- Finance draft-invoice walkthrough.
- AI closeout proposal review.

Exit criteria:

- A non-admin technician can complete their part of the workflow.
- A manager can handle exceptions and mark work invoice-ready; an Accounts user creates exactly one draft invoice.
- The work order shows deterministic projected revenue, issued parts cost, and
  margin before labor overhead.
- AI proposals are cited, immutable, and draft-only.

## Phase 5: Extract reusable industry-pack pattern

After the service pack is stable, identify which concepts are reusable:

- Request intake
- Work order state machine
- Role-scoped execution
- Exception ownership
- Manager review
- Draft-only AI proposal audit
- Deterministic handoff to ERPNext records

Move only proven reusable behavior into `ai_erp_core`. Keep service-specific
logic inside `ai_erp_service`.

## Phase 6: Choose the next industry pack

Do not pick the next pack by market size alone. Pick it when the repo has:

- at least one accessible design partner or realistic workflow evidence,
- a clear ERPNext reuse map,
- one demo workflow,
- synthetic fixtures,
- a permission model,
- a transaction safety boundary, and
- a testable AI assistance use case.

Current candidate order is in `docs/product/industry-pack-roadmap.md`.

## Phase 7: Design review gate

Before implementation of each new vertical:

- Confirm the need cannot be met by ERPNext configuration alone.
- Write or update an ADR if adding a service, datastore, provider, or external
  dependency.
- Add/update contracts before integration clients depend on the shape.
- Add tests for the highest-risk transaction and permission boundaries.
- Update the GitHub issue template or roadmap if discovery changes the
  contribution workflow.
