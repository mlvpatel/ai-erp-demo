# Performance tests

This directory holds synthetic, non-customer performance planning artifacts and
the profile used by the executable scaled smoke check.
Do not commit production exports, real logs, trace exports, dashboard
screenshots, database dumps, or client identifiers here.

Start with `service-operations-load-profile.example.json`. It defines the first
service-operations load profile: record volumes, concurrency assumptions,
scenario IDs, target latency classes, and safety evidence required before a
public performance claim.

Real benchmark results belong in private deployment evidence unless they are
fully sanitized and approved for publication.

Run the rollback-only smoke check against the local Docker site:

```sh
AI_ERP_ENV_FILE=/tmp/ai-erp-ci.env scripts/dev.sh performance-smoke
```

The command uses a fixed scaled developer dataset derived from the tracked
profile, reports the actual record counts, and records at least 20 timed samples
with nearest-rank p95. It validates role-scoped lists, draft-invoice
idempotency, and the deterministic draft-only AI path. Its local-only preflight
blocks non-`.localhost` sites and non-template control planes before writes. It
rolls its namespaced synthetic database changes back and fails when a latency
target or safety invariant is missed.

The helper supplies both the process-level allow flag and
`allow_local=True`; direct calls without both explicit opt-ins fail before the
profile can create records. It also runs focused profile, percentile, and
failure-cleanup tests before executing the timed smoke scenarios.

This is not a full-profile benchmark. True parts-issue concurrency is reported
as `EXTERNAL_CROSS_SESSION_GATE` because `scripts/dev.sh e2e-test` executes ten
issue attempts through five authenticated manager sessions. Native Frappe link search is measured for technician
and manager isolation, a side-effect-free worker batch measures queue-clear
time, and the manager-only service
profitability report is measured through permission-aware `frappe.get_list`;
a smoke pass is
`SMOKE_PASS_NOT_FULL_PROFILE` and cannot support a public capacity claim.
Database rollback cannot undo external effects; the fail-closed local/template
preflight prevents the smoke path from using an external provider.
The queue probe is restricted to `.localhost`, performs no ERP read or write,
and is the only intentional non-database side effect of the smoke command.
