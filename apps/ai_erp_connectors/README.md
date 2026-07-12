# AI ERP Connectors

Reserved future Frappe app for external-system adapters.

Connectors are not part of the first MVP unless a workflow needs a specific,
versioned integration. Keep connector code out of industry packs when the same
adapter may be reused across verticals.

## Adapter rules

- Define public API or event contracts under `contracts/` before implementing
  an adapter.
- Make every write idempotent.
- Store external identifiers and sync status on ERP records or connector-owned
  records.
- Expose failures as reviewable ERP records, not hidden logs only.
- Never let an external AI tool directly post financial, inventory, payroll,
  permission, or compliance changes.

## Candidate adapter classes

- Accounting export/import handoffs.
- Payment provider status sync.
- Document storage metadata sync.
- Carrier or warehouse-management handoffs.
- Industry-specific equipment, IoT, or field-system ingestion.

## Do not add yet

- Provider SDK dependencies without an ADR.
- Generic sync frameworks before one concrete adapter is proven.
- Secrets, sample customer payloads, or production exports.
- Unversioned webhooks or business events.

