# MVP container boundaries

For the full contributor-facing boundary map, see
`docs/architecture/system-boundaries.md`.

```text
Technician and office users
        |
        v
ERPNext / Frappe site (one tenant per database)
  - ERPNext standard records and workflows
  - ai_erp_core custom app
  - ai_erp_service custom app
  - ai_erp_connectors custom app
        |
        +-- approved API/tool boundary --> AI control plane
        |                                  - retrieval
        |                                  - model routing
        |                                  - proposed actions
        |                                  - evaluations and AI audit
        |
        +-- background jobs / notifications / integrations
```

All transactional writes stay inside the ERP site. The AI control plane receives
least-privilege data and returns proposals through the approved API boundary.
