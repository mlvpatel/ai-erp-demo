# Infrastructure

Start with Docker Compose under `compose/`. Kubernetes is intentionally empty
until production scale and operational ownership justify it.

Use `observability/` for safe monitoring and alerting examples only. Do not
commit real logs, trace exports, dashboard snapshots with customer data, alert
routes, webhook URLs, SIEM credentials, or production telemetry exports.

Keep secrets in a secrets manager or deployment environment, never in this
directory.
