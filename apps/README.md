# Custom Frappe apps

Each directory becomes an independently versioned Frappe app when development
begins. Keep imports directional: industry apps may depend on `ai_erp_core`;
the core must not depend on an industry app.

- `ai_erp_core`: shared entities, approval policy, audit/event helpers, and
  module registry.
- `ai_erp_service`: field service, work orders, technician closeout, and parts
  traceability.
- `ai_erp_distribution`: later wholesale/distribution capabilities.
- `ai_erp_manufacturing`: later manufacturing-specific capabilities.
- `ai_erp_connectors`: versioned adapters to external accounting, payments,
  documents, or industry systems.

Future app folders are intentionally documentation-only until their discovery
entry gate passes. Use `docs/product/industry-pack-design-template.md` before
turning a reserved folder into generated Frappe app code.
