# Infrastructure

Use Docker Compose under `compose/` for development. The credential-free,
plan-only AWS foundation lives under `aws/terraform/`; its use and explicit
limitations are documented in its README. The AWS ECS production reference is
documented in
[`docs/architecture/aws-production-reference.md`](../docs/architecture/aws-production-reference.md)
and ADR-0007. No repository script or CI job applies it. It must not be applied
until its budget, identity, recovery, data, support, and legal gates are
approved. Kubernetes remains intentionally empty.

Use `observability/` for safe monitoring and alerting examples only. Do not
commit real logs, trace exports, dashboard snapshots with customer data, alert
routes, webhook URLs, SIEM credentials, or production telemetry exports.

The reserved `security/` directory is intentionally empty; design-time
security guidance lives in [`docs/security/`](../docs/security/README.md).

Keep secrets in a secrets manager or deployment environment, never in this
directory.
