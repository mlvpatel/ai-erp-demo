# Tenant isolation

The MVP uses Frappe's multi-site model: one tenant per Frappe site and
database. Application code must not retrofit shared-row tenancy with a custom
`tenant_id` field.

## MVP rules

- Tenant identity lives at the Frappe site and API edge.
- ERP transaction state stays inside the tenant's Frappe/ERPNext site database.
- The AI control plane receives `tenant_site` only as audit scope. It is not an
  authorization decision and does not grant access to another tenant.
- Business events include `tenant_site` so downstream consumers can route and
  audit events, not to bypass ERP permissions.
- Cross-tenant analytics, shared-row tenancy, and tenant-level data projection
  need a future ADR, explicit access control, and a new test plan.

## Implementation expectations

For any feature that crosses a site boundary or leaves the Frappe site:

1. Use `frappe.local.site` as the tenant-site audit scope.
2. Do not add app-level `tenant_id`, `tenantId`, or `X-Tenant-ID` shortcuts.
3. Keep authorization tied to Frappe permissions, user roles, and service
   credentials, not caller-supplied tenant labels.
4. Keep AI requests and future event envelopes versioned under `contracts/`.
5. Add tests or static evidence for tenant-site scope before enabling the path.

The machine-readable tenant isolation contract is
`config/tenant-isolation.json`. The static quality gate runs
`scripts/check-tenant-isolation.py` so ADRs, contracts, payload builders, and
docs remain aligned.
