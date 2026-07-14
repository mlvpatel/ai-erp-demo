# AI ERP Manufacturing

Configured demo for light manufacturing workflows using standard ERPNext only.
Human validation remains pending.

No Frappe app is generated here yet. ERPNext already has manufacturing modules,
BOMs, work orders, job cards, and stock flows, so this pack should stay empty
until discovery proves a gap that configuration cannot cover.
The current [hypothesis brief](../../docs/discovery/light-manufacturing-industry-pack.md)
is synthetic and still awaits design-partner validation.

## Configured demo

The synthetic setup and role-separated manual walkthrough are documented in
[`light-manufacturing-configured-demo.md`](../../docs/runbooks/light-manufacturing-configured-demo.md).
The seeder creates only master data, a draft BOM, and a draft Sales Order. It
never submits manufacturing, stock, or financial records. This folder remains
documentation-only.

## Candidate proof workflow

Make-to-order quote -> BOM/work-order review -> material availability exception
-> production status summary -> invoice-ready handoff.

## Reuse first

- ERPNext Manufacturing for BOMs, work orders, job cards, and production plans.
- ERPNext Stock for material availability and valuation.
- ERPNext Selling for quotations and sales orders.
- ERPNext Projects only when production work must be connected to project
  delivery.

## Custom behavior only if proven

- AI-drafted production exception summaries with cited source documents.
- Material-shortage explanation workflows.
- Approval/audit wrappers around risky production changes.
- Industry-specific quality checks that cannot be represented by ERPNext
  quality inspection configuration.

## Do not add yet

- A second MRP engine.
- Autonomous BOM, work-order, or stock-entry posting from AI output.
- Shop-floor scheduling abstractions before real scheduling discovery.
- Custom costing logic that bypasses ERPNext valuation/accounting controls.
