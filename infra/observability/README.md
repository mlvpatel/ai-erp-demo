# Observability

This directory contains safe, non-secret observability guidance and examples.
It intentionally does not vendor Prometheus, Grafana, OpenTelemetry collectors,
SIEM rules, or hosted monitoring configuration.

Use deployment-specific tooling to collect metrics, logs, traces, and alerts.
Keep secrets, customer data, prompt bodies, provider responses, backup storage
URLs, trace exports, and production log archives out of this repository.

Minimum deployment signals:

- Frappe site availability, error rate, latency, scheduler health, and worker
  availability.
- Queue backlog, stuck jobs, failed background jobs, and retry exhaustion.
- MariaDB and Redis availability, connection failures, disk pressure, and
  memory pressure.
- Backup freshness, restore-drill evidence, and checksum verification.
- AI control-plane `/healthz`, request validation failures, provider failures,
  latency, output safety rejections, and unsupported-action attempts.
- ERP safety events for permission bypass attempts, tenant-boundary failures,
  AI approval-bypass attempts, idempotency conflicts, and connector delivery
  failures.

`alert-rules.example.yml` names expected alerts and metric shapes. Treat it as
a vendor-neutral starting point, not a production-ready monitoring stack.
