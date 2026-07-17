# Dependency update workflow

Dependency updates are useful, but this repo treats ERP runtime changes as
product-risk changes, not routine chores. Do not auto-merge dependency PRs.

## What Dependabot covers

`.github/dependabot.yml` opens monthly pull requests for:

- GitHub Actions versions.
- Python package metadata in `services/ai_control_plane/`.
- Python package metadata in the custom Frappe apps.
- The AI control-plane Dockerfile base image.
- The pinned Playwright package under `tests/e2e/`.

Dependabot visibility is intentionally narrow. It does not prove that an ERP
runtime upgrade is safe.
The source-of-truth automation map is `config/dependency-updates.json`; the
static quality gate runs `scripts/check-dependency-updates.py` so Dependabot
entries, labels, manual-only pins, and this workflow stay aligned.
For upstream ERP runtime changes, also follow
`docs/workflows/upstream-upgrade-readiness.md`.

## Manual-only updates

Update these only through an explicit maintainer PR:

- `FRAPPE_COMMIT` in `development/.env.example`.
- `ERPNEXT_COMMIT` in `development/.env.example`.
- digest-pinned `MARIADB_IMAGE`, `REDIS_IMAGE`, and `FRAPPE_BENCH_IMAGE`.
- digest-pinned `PLAYWRIGHT_IMAGE`, kept at the same version as
  `@playwright/test` in `tests/e2e/package.json`.
- Python version changes.
- Frappe/ERPNext branches.
- dependencies that affect money, stock, permissions, payroll, compliance,
  AI proposal approval, or contract behavior.

## Required checks by update type

| Change | Required checks |
| --- | --- |
| GitHub Actions only | `scripts/run-quality-gates.sh` and GitHub CI. |
| AI control-plane dependency or Dockerfile | Control-plane unit tests and contract tests. |
| Custom Frappe app dependency or packaging metadata | Static quality gates plus the service workflow integration gate. |
| Playwright package or `PLAYWRIGHT_IMAGE` | Static gates plus `scripts/dev.sh e2e-test`; package and image versions must match. |
| Frappe/ERPNext commit or image digest | Upstream upgrade readiness check, reproducibility check, Docker Compose config check, site migration, service integration tests, and local demo seed. |
| Security-sensitive dependency | Threat-model review and a short note in the PR explaining risk and rollback. |

## Review checklist

- Does the change alter any public API, event schema, DocType, fixture, or
  workflow state?
- Does it change how permissions, tenant/site context, or audit records work?
- Can it create duplicate Stock Entries, Sales Invoices, or external writes on
  retry?
- Does it change what data leaves the Frappe site for AI processing?
- Is rollback clear if the update fails migration or demo checks?

## Release note rule

If the update changes Frappe/ERPNext pins, runtime image digests, AI provider
behavior, or transaction-authoritative ERP behavior, add a short note to
`CHANGELOG.md` before merging.
