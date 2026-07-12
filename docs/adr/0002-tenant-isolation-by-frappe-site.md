# ADR-0002: Isolate each tenant by Frappe site and database

- Status: Accepted
- Date: 2026-07-10
- Owners: AI ERP Demo

## Context

The MVP must prevent data exposure between customers while remaining simple to
self-host and operate. A shared `tenant_id` model with custom row-level
security would duplicate tenancy logic through every ERPNext extension.
Production use still requires the technical spike to verify this accepted
boundary against the pinned Frappe/ERPNext release.

## Decision

Use Frappe's multi-site model: one tenant per site/database, with shared
application code and infrastructure. Keep tenant identity at the site and API
edge, not as an application-level `tenant_id` retrofit.

Use the database configuration officially supported by the selected ERPNext
release for the first technical spike. Do not commit to PostgreSQL/pgvector for
the ERP transaction store until compatibility is verified; keep retrieval data
behind the AI control-plane boundary.

## Consequences

- Tenant backup, restore, export, and deletion are naturally isolated.
- Cross-tenant analytics needs an explicit, access-controlled projection later.
- The deployment tooling must provision a site, database, domain, and backup
  policy as one tenant unit.

## Alternatives considered

- Shared database with `tenant_id` and database RLS: rejected for the MVP due
  to invasive customisation and greater isolation risk.
- One deployment per tenant: deferred; use only for customers whose isolation
  or residency requirements require it.
