# Light-manufacturing industry-pack discovery brief

- Status: hypothesis only
- Lifecycle decision: entry gate not started; remain **reserved**
- Design partner validation: pending
- Evidence quality: ERPNext capability mapping is verified; workflow and
  performance targets are assumptions until a named design partner approves
  them
- Data policy: synthetic fixtures only

## Industry and user

- Industry: make-to-order light manufacturing
- Primary user: production planner
- Secondary users: sales coordinator, material handler, production supervisor,
  finance reviewer
- Process owner: deferred until a design partner is named
- System of record: ERPNext for quotations, BOMs, production Work Orders, stock
  movements, and invoices

## Business job and measurable signal

> When a make-to-order job is accepted, the production planner needs a cited
> material-availability and schedule-exception summary so that a human can
> release feasible work without unsafe stock or financial automation.

Assumed success signals are: shortages are reproducible from ERP records,
unauthorized users cannot release or complete work, and the planner reaches a
release decision from no more than three ERP views. Baseline, latency, volume,
and accuracy targets are deferred to pilot discovery.

## First proof workflow

Start: an accepted synthetic make-to-order quotation or Sales Order.

End: an authorized production Work Order release, or a planner-owned material
exception awaiting an explicit decision.

1. Reuse an approved ERPNext Item and BOM revision.
2. Create the production Work Order through native ERPNext behavior.
3. Calculate material demand and availability deterministically from the BOM,
   warehouses, and stock ledger.
4. Detect missing material, stale BOM, or scheduling exceptions.
5. Ask AI only for a cited production-exception summary.
6. Let an authorized planner choose procure, reschedule, revise the BOM through
   its governed process, or stop.
7. Release and complete manufacturing/stock transactions only through ERPNext
   permissions and approvals.

## ERPNext reuse map

| Need | Reused record/module | Configuration first | Unverified custom gap |
| --- | --- | --- | --- |
| Customer demand | Quotation, Sales Order / Selling | Yes | None |
| Product definition | Item, BOM / Manufacturing | Yes | Revision decision view |
| Production execution | Work Order, Job Card | Yes | Cross-record exception view |
| Materials | Material Request, Stock Entry, Bin | Yes | Planner shortage workbench |
| Billing handoff | Delivery Note, Sales Invoice | Yes | None |

No custom behavior is proven yet. The reserved app must remain
documentation-only until a design partner demonstrates a gap that ERPNext
configuration, workflows, permissions, reports, or print formats cannot meet.

## AI and transaction boundary

AI may retrieve, summarize, explain material/schedule exceptions, or draft a
planner note. It must cite permission-visible source records and abstain on
missing or conflicting BOM/stock evidence. It cannot approve a BOM, release or
complete a Work Order, create or submit a Stock Entry, post finance, change
permissions, purchase material, or communicate externally.

## Permissions and approval

| Role | Allowed | Approval boundary | Forbidden |
| --- | --- | --- | --- |
| Sales coordinator | Maintain quotation/order drafts | Sales approval policy | BOM and stock mutation |
| Production planner | Create/review draft Work Orders and exceptions | Production Manager releases work | Stock posting and finance submission |
| Material handler | Execute assigned material steps | Stock role submits controlled movement | BOM change, unrelated warehouses, finance |
| Production manager | Approve/release production under ERP policy | Segregation-of-duties policy | Finance unless separately authorized |
| Finance reviewer | Review downstream billing | Finance role submits | Manufacturing and stock mutation |

Tenant isolation is one Frappe site/database per tenant. Availability queries,
reports, citations, and AI context must use the requesting user's permissions.

## Synthetic fixtures and acceptance cases

Fixtures should include a versioned BOM, two warehouses, one complete material
set, one shortage, one unauthorized handler, and an unrelated tenant/site
dataset. No customer BOM, formula, routing, supplier, or employee export is
permitted.

- Planner can inspect only permitted BOM, order, and warehouse records.
- Missing material or stale BOM blocks release deterministically.
- Repeating an approval/action cannot duplicate Work Orders or Stock Entries.
- AI output cites visible records and cannot release manufacturing or stock.
- A second tenant/site cannot be discovered through list, search, report, or AI.
- Provider failure leaves the exception in a reviewable non-mutating state.

## Exit decision

- Ready to remain a reserved documentation-only pack: **yes**.
- Ready to generate or expand a Frappe app: **no**.
- Needs more discovery: **yes**, from a named light-manufacturing design partner.
- Configuration-only outcome remains possible.
