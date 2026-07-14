# Distribution industry-pack discovery brief

- Status: configured demo; product hypothesis not validated
- Lifecycle decision: configured demo using standard ERPNext only
- Design partner validation: pending
- Evidence quality: ERPNext capability mapping is verified; user needs and
  success targets are assumptions until a named design partner approves them
- Data policy: synthetic fixtures only
- Configured evidence: local-only synthetic seed plus the standard ERPNext
  walkthrough in `docs/runbooks/distribution-configured-demo.md`

## Industry and user

- Industry: wholesale and regional distribution
- Primary user: distribution operations manager
- Secondary users: sales coordinator, warehouse picker/packer, delivery
  coordinator, finance reviewer
- Process owner: deferred until a design partner is named
- System of record: ERPNext for orders, stock, pick lists, deliveries, and
  invoices

## Business job and measurable signal

> When an accepted order cannot be fulfilled as promised, the operations
> manager needs a cited shortage and delivery-exception summary so that a human
> can choose the next safe action.

Assumed success signals are: the picker completes allowed steps without Stock
Manager privileges, every shortage is linked to source records, and the manager
can decide an exception without opening more than three ERP records. Baseline
and target values are deferred to pilot discovery.

## First proof workflow

Start: a submitted Sales Order with synthetic stock availability.

End: an authorized Delivery Note handoff, or a manager-owned exception awaiting
an explicit decision.

1. Reuse ERPNext Sales Order and stock availability.
2. Create and assign a Pick List using native permissions and workflow state.
3. Let the picker record actual picked quantities; do not submit stock movement
   through AI.
4. Detect a deterministic shortage or delivery-date exception.
5. Ask AI only for a cited explanation draft from permission-visible records.
6. Let an authorized manager choose backorder, substitution, partial delivery,
   or cancellation through deterministic ERP validation.
7. Create or submit the Delivery Note only through the authorized ERP workflow.

## ERPNext reuse map

| Need | Reused record/module | Configuration first | Unverified custom gap |
| --- | --- | --- | --- |
| Customer demand | Sales Order / Selling | Yes | None |
| Pick and pack | Pick List / Stock | Yes | Role-specific mobile ergonomics |
| Availability | Bin, Warehouse, Stock Ledger | Yes | Cross-record exception view |
| Delivery | Delivery Note / Stock | Yes | Exception decision audit view |
| Billing | Sales Invoice / Accounting | Yes | None |

No custom behavior is proven yet. The reserved app must stay documentation-only
until a design partner demonstrates a gap that configuration, permissions,
workflow, reports, or print formats cannot meet.

## AI and transaction boundary

AI may retrieve, summarize, explain a shortage, or draft a delivery exception.
It must cite permission-visible source records, abstain when evidence is
missing, and remain subject to human review. It cannot reserve stock, change a
Sales Order, submit a Pick List or Delivery Note, post inventory or finance,
change permissions, or contact a customer.

## Permissions and approval

| Role | Allowed | Approval boundary | Forbidden |
| --- | --- | --- | --- |
| Sales coordinator | Create/update draft Sales Orders | Sales approval policy | Stock posting and invoice submission |
| Picker/packer | Read assigned pick work; record picked quantities | Stock Manager submits controlled movement | Other warehouses, substitutions, financial records |
| Distribution manager | Review availability and exceptions | Chooses exception resolution | Accounting submission unless separately authorized |
| Finance reviewer | Review/create draft invoice under ERP policy | Finance role submits | Warehouse mutation |

Tenant isolation is one Frappe site/database per tenant. Search, reports, AI
context, and citations must use the requesting user's Frappe permissions.

## Synthetic fixtures and acceptance cases

Fixtures should include two warehouses, two users with different assignments,
one fully available order, one partial shortage, and one unrelated tenant/site
dataset. No customer export is permitted.

- Picker sees only assigned work and permitted warehouses.
- An unavailable quantity blocks unsafe progression deterministically.
- Repeating an exception action does not duplicate a delivery or stock move.
- AI output cites visible records and cannot mutate stock or finance.
- A second tenant/site cannot be discovered through list, search, report, or AI.
- Provider failure leaves the exception in a reviewable non-mutating state.

## Exit decision

- Ready to remain a reserved documentation-only pack: **yes**.
- Ready to run as a standard ERPNext configured demo: **yes**.
- Ready to generate or expand a Frappe app: **no**.
- Needs more discovery: **yes**, from a named distribution design partner.
- Configuration-only outcome remains possible.
