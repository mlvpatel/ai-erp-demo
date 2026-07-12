# Observability readiness

Use this checklist before a broad demo, public preview, or production-use
discussion. The goal is not to add a monitoring vendor to the repository; it is
to make the safety-critical signals explicit before real business data exists.

## Principles

- Prefer deployment-platform metrics, Frappe/ERPNext operational signals, and
  standard logs before adding a new observability service.
- Keep telemetry free of secrets, customer contact details, service addresses,
  attachment contents, prompt bodies, model keys, database credentials, and
  backup storage URLs.
- Log stable record identifiers, event types, status, durations, source hashes,
  and error classes. Use private operations tooling to correlate them with
  sensitive records when needed.
- Route safety alerts privately. Do not paste raw logs or trace payloads into
  public GitHub issues.
- Treat observability as evidence for recovery, incident response, and audit;
  it must not become a second store of customer data.

## Minimum signal map

| Area | Signals to capture | Alert when |
| --- | --- | --- |
| Frappe site | HTTP availability, request error rate, p95 latency, active workers, scheduler status. | Site is down, error rate spikes, scheduler stops, or workers are unavailable. |
| Queues and jobs | Queue backlog, stuck jobs, failed background jobs, retry count. | Queue age grows, jobs repeatedly fail, or scheduler tasks stop processing. |
| MariaDB and Redis | Availability, connection failures, disk pressure, memory pressure. | Database or Redis is unreachable, near capacity, or repeatedly reconnecting. |
| Backup and restore | Last successful backup timestamp, restore-drill timestamp, checksum verification. | Backup is stale, restore drill is overdue, or checksum verification fails. |
| AI control plane | `/healthz`, request validation failures, provider failures, latency, output safety rejections. | Error rate rises, provider calls fail, validation rejects unexpected payloads, or unsupported-action attempts appear. |
| ERP safety | Unauthorized role attempts, idempotency conflicts, AI approval-bypass attempts, tenant-boundary failures. | Any tenant-boundary failure or unapproved financial, stock, payroll, access-control, or compliance mutation path is observed. |
| Integrations | Event delivery failures, duplicate event keys, connector retry exhaustion, contract validation failures. | Events cannot be delivered, replay is unsafe, or connector failures become hidden logs only. |

## What belongs in this repository

- Safe example alert names and non-secret metric names in
  `infra/observability/alert-rules.example.yml`.
- Runbooks and workflow docs that explain what to monitor and how to respond.
- Static checks that keep observability guidance aligned with incident,
  recovery, security, and release docs.

## What does not belong in this repository

- Real log exports, trace exports, dashboard screenshots with customer data,
  production alert history, database snapshots, customer names, addresses,
  phone numbers, emails, API keys, model prompts, or provider responses.
- Deployment-specific webhook URLs, alert routing secrets, SIEM credentials, or
  managed-monitoring workspace identifiers.

## Pre-production gate

Before using real client data:

1. Name the owner for alert triage and after-hours escalation.
2. Configure private monitoring for Frappe, MariaDB, Redis, queue workers,
   scheduler jobs, AI control-plane health, backup freshness, and disk usage.
3. Configure safety alerts for tenant-boundary failures, permission bypasses,
   AI approval bypasses, idempotency conflicts, and connector replay failures.
4. Run a restore drill and confirm observability can prove the drill happened.
5. Confirm logs, metrics, traces, and screenshots do not contain secrets,
   customer data, prompt bodies, backup URLs, or credentials.
6. Run `python3 scripts/check-observability-readiness.py`.
7. Align performance alert thresholds with
   `docs/workflows/performance-readiness.md`.

## Verification

Run:

```sh
python3 scripts/check-observability-readiness.py
scripts/run-quality-gates.sh
```

The checker is static. It proves the repository has the right public
observability boundaries. A deployed environment still needs live monitoring,
alert routing, retention policy, and private incident evidence.
