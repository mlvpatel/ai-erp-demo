# AI ERP Demo

Private zero-cost local synthetic demo for a governed, AI-assisted
field-service ERP. The product is built as a set of
custom Frappe apps on top of ERPNext; upstream Frappe and ERPNext are pinned as
development checkout dependencies and are not copied into this repository.

The repository and its custom apps are licensed under `AGPL-3.0-only`; see
[`LICENSE`](LICENSE) and the accepted
[ADR-0005](docs/adr/0005-root-license-required-before-github-publish.md).
Upstream ERPNext and Frappe dependencies retain their own licenses and are not
copied into this repository.

## Product boundary

- `apps/` contains reusable ERP extensions and industry packs.
- `services/ai_control_plane/` contains the isolated AI orchestration service.
- `contracts/` contains versioned public API and business-event contracts.
- `infra/` contains deployment and operational configuration only.
- `docs/` is the source of truth for product decisions and architecture.

Do not create generic `frontend/` and `backend/` folders. Frappe already owns
the ERP web UI, REST API, permissions, workflow engine, background workers,
and real-time layer. A separate UI or service is added only when the core
cannot serve the use case.

## Layout

```text
.
├── AGENTS.md                    # Working rules for people and coding agents
├── .agents/
│   └── skills/                   # Repo-local Codex delivery workflows
├── apps/                        # Custom Frappe apps only
│   ├── ai_erp_core/             # Horizontal capabilities and shared policies
│   ├── ai_erp_service/          # First vertical: field service
│   ├── ai_erp_distribution/     # Reserved boundary; standard configured demo only
│   ├── ai_erp_manufacturing/    # Reserved boundary; standard configured demo only
│   └── ai_erp_connectors/       # External-system adapters
├── services/
│   └── ai_control_plane/        # Model gateway, tools, evals, audit controls
├── contracts/
│   ├── openapi/                 # Versioned external API specifications
│   └── events/                  # Versioned business-event contracts
├── docs/
│   ├── adr/                     # Architecture decision records
│   ├── discovery/               # Interview findings and domain maps
│   ├── product/                 # ICP, roadmap, jobs-to-be-done, KPIs
│   ├── architecture/            # C4 diagrams and data boundaries
│   ├── security/                # Threat models and data classification
│   ├── runbooks/                # Support, backup, recovery, incident guides
│   └── workflows/               # Repeatable engineering workflows
├── infra/
│   ├── compose/                 # Local and first-production Docker Compose
│   ├── kubernetes/              # Later production manifests, not MVP work
│   ├── observability/           # OpenTelemetry, dashboards, alerts
│   └── security/                # Non-secret policy and scanning configuration
├── tests/
│   ├── contract/                # API and event compatibility tests
│   ├── e2e/                     # Pinned synthetic Playwright role/route smoke
│   ├── fixtures/                # Synthetic, non-customer test data
│   └── performance/             # Synthetic profile + rollback-only smoke runner
├── scripts/                     # Safe, documented developer automation
├── development/                 # Tracked bootstrap config; local bench is ignored
├── config/                      # Checked-in, environment-safe defaults
├── agents/                      # Optional role briefs for parallel contributors
└── .github/                     # CI, templates, and repository automation
```

## First build order

1. Review the July 2026 stack decision and open-source ERP scan in `docs/`.
   Read [docs/architecture/system-context-and-repository-map.md](docs/architecture/system-context-and-repository-map.md),
   [docs/architecture/system-boundaries.md](docs/architecture/system-boundaries.md),
   and [docs/architecture/domain-data-model.md](docs/architecture/domain-data-model.md)
   before placing new code.
2. Generate `apps/ai_erp_core/` as a Frappe app; never modify upstream core.
3. Build the service-and-parts industry pack in `apps/ai_erp_service/`.
4. Add AI only through `services/ai_control_plane/`, with explicit approvals.
5. Add contracts, tests, and CI before adding further industry packs.

See [ROADMAP.md](ROADMAP.md) for the current staged plan and
[docs/product/public-positioning.md](docs/product/public-positioning.md) for the
public GitHub positioning.
See [BACKLOG.md](BACKLOG.md) for demo-release work, deferred pilot gates, and
safe first issue ideas.
See [docs/product/requirements-traceability.md](docs/product/requirements-traceability.md)
to audit original requirements against current evidence.

## Local development

The tracked development configuration starts a Frappe Bench container, MariaDB,
Redis, and the AI control plane. The actual Frappe Bench checkout, tenant site,
database, and local credentials remain ignored under `development/frappe-bench/`.

Follow [development/README.md](development/README.md) to create the local ERP
site. It clones Frappe/ERPNext v16, pins them to checked-in commit hashes, and
does not modify upstream code.
Before changing Frappe/ERPNext commits, runtime image digests, Python, or
Frappe Bench assumptions, follow
[docs/workflows/upstream-upgrade-readiness.md](docs/workflows/upstream-upgrade-readiness.md).

For a contributor-friendly command list, run `scripts/dev.sh help`. For the
first service-operations demo path, follow
[docs/runbooks/local-demo.md](docs/runbooks/local-demo.md).
An `implemented` claim means checked-in source and an executable verification
path exist. It does not mean production deployment, human UAT, legal approval,
capacity, or recovery evidence exists. Run `scripts/dev.sh service-test` and
`scripts/dev.sh e2e-test` on a disposable synthetic stack before relying on the
field-service behavioral claims. The current demo and production-pilot gate
status is recorded in
[config/pilot-readiness.json](config/pilot-readiness.json). The local synthetic
demo does not require AWS, live OpenAI, legal approval, human UAT, a restore
drill, or a production go/no-go decision; those remain separate pilot gates.
For a screenshot, GIF, maintainer walkthrough, or first public demo issue, use
[docs/runbooks/demo-script.md](docs/runbooks/demo-script.md) so the
service-operations demo path stays aligned with verified MVP claims.
Before any real client data, backup, restore drill, or incident response work,
read [docs/workflows/operations-readiness.md](docs/workflows/operations-readiness.md),
[docs/runbooks/backup-restore.md](docs/runbooks/backup-restore.md), and
[docs/runbooks/incident-response.md](docs/runbooks/incident-response.md).
Before adding monitoring, alerts, dashboards, traces, or log-retention guidance,
read [docs/workflows/observability-readiness.md](docs/workflows/observability-readiness.md).
Before changing list/search/report behavior, queues, inventory-heavy flows, or
public performance claims, read
[docs/workflows/performance-readiness.md](docs/workflows/performance-readiness.md).

## Zero-cost demo evidence

These screenshots were captured from the local synthetic site after the
Docker-backed role journey passed. They demonstrate the field-service workflow;
they are not human UAT, production, capacity, recovery, or legal evidence.

**Technician execution:** time, declared parts, submitted stock link, and
synthetic closeout evidence remain on the permission-scoped work order.

![Synthetic service work-order execution](docs/media/demo/service-work-order-execution.jpg)

**Manager/finance handoff:** the manager marks the work invoice-ready and the
separately authorized Accounts user owns the linked draft Sales Invoice.

![Synthetic manager and finance handoff](docs/media/demo/manager-finance-handoff.jpg)

**Governed AI draft:** cited sources, human review, and the `Draft Only` policy
remain visible without performing an ERP transaction.

![Synthetic cited draft-only AI proposal](docs/media/demo/ai-proposal-draft-only.jpg)

## GitHub publication

Before making the repository public, follow
[docs/runbooks/github-publication.md](docs/runbooks/github-publication.md).
The runbook keeps the first push clean by checking the license decision,
ignored Frappe Bench state, reproducible pins, CI expectations, and AI safety
boundaries.

Community and publication guardrails are in `CONTRIBUTING.md`,
`CODE_OF_CONDUCT.md`, `GOVERNANCE.md`, `SECURITY.md`, `SUPPORT.md`, and
`CHANGELOG.md`.

Use `scripts/check-open-source-ready.sh` for a non-destructive readiness check.
Use `python3 scripts/check-publication-secrets.py` when fixtures, docs, issue
templates, or examples change.
Use `python3 scripts/check-operations-readiness.py` when recovery, incident,
publication exclusion, support, or security docs change.
Use `python3 scripts/check-observability-readiness.py` when monitoring,
alerting, logging, trace, dashboard, or observability docs change.
Use `python3 scripts/check-performance-readiness.py` when performance profiles,
load-sensitive workflows, reports, queues, or scalability docs change.
Use `python3 scripts/check-upstream-upgrade-readiness.py` when Frappe/ERPNext
pins, runtime image digests, or upstream upgrade docs change.
Use `scripts/check-open-source-ready.sh --release` only after every public
release gate is complete.

## Rules

- No secrets, customer data, production database dumps, backup artifacts, or
  model keys in Git.
- Money, stock, payroll, and permissions are deterministic ERP actions; AI can
  only prepare a proposal for an approved workflow.
- Keep customer- or vertical-specific behavior in its industry pack, not in
  the global `ai_erp_core` app.
