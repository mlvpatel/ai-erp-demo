# AI ERP quality gates

## Discovery gate

- Name the target user, business outcome, process owner, and measurable success
  signal.
- Mark each requirement as verified, assumed, or deferred.
- Identify the system of record and integration owner for every affected entity.

## Design gate

- Define role permissions, approval states, audit events, tenant scope, and
  error/retry behavior.
- Choose the smallest existing Frappe capability that meets the requirement.
- Document any new service, datastore, model provider, or public contract in an
  ADR before implementation.

## AI gate

- Specify the allowed tools and prohibited state changes.
- Define human approval or deterministic validation for any action proposal.
- Define evidence sources, retention, evaluation cases, cost limits, and an
  abstention path when confidence or data quality is inadequate.

## Release gate

- Pass focused business-rule, permission, and contract tests.
- Run an end-to-end workflow with a non-administrator role.
- Verify tenant isolation, structured logs, monitoring signals, and rollback or
  recovery behavior.
