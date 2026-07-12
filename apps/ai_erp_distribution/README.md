# AI ERP Distribution

Reserved future industry pack for wholesale, distribution, and order-fulfillment
workflows.

No Frappe app is generated here yet. Keep this directory lightweight until the
entry gate in `docs/product/industry-pack-roadmap.md` is satisfied.

## Candidate proof workflow

Sales Order -> pick/pack review -> stock availability exception -> delivery
handoff -> delivery exception summary.

## Reuse first

- ERPNext Selling for customers, quotations, sales orders, and delivery notes.
- ERPNext Stock for warehouses, items, bins, batches, serial numbers, and stock
  ledger entries.
- ERPNext Buying for supplier-side replenishment where the proof workflow needs
  it.
- ERPNext Accounting for invoice and payment records.

## Custom behavior only if proven

- Pick/pack exception triage that ERPNext configuration cannot express cleanly.
- AI-drafted delivery or shortage explanations with cited source records.
- Idempotent external carrier or warehouse-system adapter handoffs.

## Do not add yet

- A separate warehouse-management engine.
- Autonomous stock moves from AI output.
- Carrier integrations before a concrete adapter contract exists.
- Generic forecasting or replenishment logic without discovery evidence.

