# AI ERP Distribution

Configured demo for wholesale, distribution, and order-fulfillment workflows
using standard ERPNext only. Human validation remains pending.

No Frappe app is generated here yet. Keep this directory lightweight until the
entry gate in `docs/product/industry-pack-roadmap.md` is satisfied.
The current [hypothesis brief](../../docs/discovery/distribution-industry-pack.md)
is synthetic and still awaits design-partner validation.

## Configured demo

The synthetic setup and role-separated manual walkthrough are documented in
[`distribution-configured-demo.md`](../../docs/runbooks/distribution-configured-demo.md).
The seeder creates only master data and a draft Sales Order. It never submits a
Sales Order, Pick List, Delivery Note, stock transaction, or financial record.
This folder remains documentation-only.

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
