# Performance readiness

Use this checklist before claiming that the AI ERP Demo can handle realistic ERP
record volumes, before changing list/search/report behavior, and before
expanding inventory-heavy industry packs.

The goal is not to invent a synthetic benchmark trophy. The goal is to make
performance evidence boring, repeatable, and tied to the ERP workflows that can
hurt a real business when they become slow or unsafe.

## Principles

- Reuse Frappe/ERPNext list views, reports, indexes, background jobs, and
  database behavior before adding a new caching layer or search service.
- Performance fixtures must be synthetic and deterministic. Never use customer
  exports, production logs, production database snapshots, or real contact
  details.
- Measure role-scoped behavior. A fast Administrator path does not prove that a
  technician, manager, or integration user has a usable workflow.
- Measure safety invariants under retry and concurrency. Load testing must not
  create duplicate Stock Entries, duplicate draft Sales Invoices, approval
  bypasses, tenant-boundary leaks, or AI side effects.
- Record environment, data profile, command, commit, result, and regression
  notes privately for real deployments. Keep public repo examples free of real
  telemetry or customer data.

## Minimum performance surfaces

| Surface | What to measure | Before accepting |
| --- | --- | --- |
| Service Work Order list and filters | p95 list latency with technician and manager roles over realistic work-order counts. | p95 latency target is named, slow filters are explained, and role restrictions still hold. |
| Search and link fields | Search latency for customer, service location, item, and work-order references. | Search does not require customer data exports and does not bypass permissions. |
| Invoice-ready workflow | Manager closeout review and invoice-ready transition, followed by Accounts-role draft Sales Invoice creation. | The action remains idempotent and draft-only under retry. |
| Parts issue and stock handoff | Manager-triggered Material Issue creation with concurrent retries. | Exactly one submitted Stock Entry is linked per part row. |
| AI closeout draft | AI payload build, control-plane validation, proposal storage, and review. | AI remains draft-only, cited, and unable to mutate ERP records. |
| Background jobs and queues | Queue age, failed jobs, and scheduler behavior under seeded record volume. | Queue backlog clears within the deployment target and failures are observable. |
| Reports and dashboards | Service profitability, exception, and invoice-readiness report timing. | Reports stay scoped to allowed records and do not require unsafe denormalization. |

## Example load profile

The checked-in example profile lives at
`tests/performance/service-operations-load-profile.example.json`. It defines
synthetic record volumes, scenario IDs, target latency classes, and evidence
requirements. Treat it as a planning contract, not as a benchmark result.

Before a public performance claim or production pilot, copy the profile into a
private test plan, run it against a clean environment, and store results outside
the repository if they contain infrastructure identifiers, logs, or customer
context.

## Change gate

Run a performance review when a change touches:

- DocType fields used in list, search, filters, permissions, or reports;
- stock issue, invoice creation, profitability, closeout, or AI proposal flows;
- background jobs, queues, scheduler behavior, event emission, or connectors;
- data access patterns over Service Request, Service Work Order, AI Proposal,
  Stock Entry, Sales Invoice, Item, Customer, or Warehouse records;
- new industry packs with inventory, manufacturing, distribution, asset, or
  purchasing volume.

At minimum, document:

1. expected record volume and concurrency;
2. role and tenant scope tested;
3. p95 or p99 latency target;
4. idempotency and authorization invariants under retry;
5. queue/backlog expectation;
6. rollback or mitigation if the target is missed.

## Executable scaled smoke check

After migrating the local Docker site, run:

```sh
AI_ERP_ENV_FILE=/tmp/ai-erp-ci.env scripts/dev.sh performance-smoke
```

The command uses a fixed scaled synthetic developer dataset, reports its actual
record counts, measures nearest-rank p95 with at least 20 samples per role, and
checks technician/manager list isolation, the manager-only profitability report,
draft-invoice safety, and deterministic draft-only AI invariants. Synthetic
database changes are rolled back, including on failure. Native Frappe link
search proves technician/manager isolation, and a side-effect-free local worker
batch measures queue-clear time. True parts-issue concurrency is delegated to
the five-session browser gate and reported as `EXTERNAL_CROSS_SESSION_GATE`, so the smoke status remains
`SMOKE_PASS_NOT_FULL_PROFILE`.

The command fails closed before writes unless it runs on a `.localhost` site
through the local Docker control plane with the deterministic template provider.
This matters because a database rollback cannot undo an external provider call.

This scaled command detects regressions on a developer machine. It is not a
capacity result and must not be described as full-profile validation or used
for a public performance claim.

## Verification

Run the static check:

```sh
python3 scripts/check-performance-readiness.py
scripts/run-quality-gates.sh
AI_ERP_ENV_FILE=/tmp/ai-erp-ci.env scripts/dev.sh performance-smoke
```

The static checker proves the public repository keeps the performance contract
visible and safe. The scaled smoke command adds executable regression evidence;
neither replaces a full load test on declared deployment hardware.
