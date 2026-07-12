# Audit remediation status — 2026-07-12

## Provenance and safety

This current-state record was derived from the read-only reports
`erp_demo_audit_and_gap_analysis.md` (2026-07-11) and
`ERP-demo-audit-remediation-2026-07-12.md` (2026-07-12). The raw reports are
intentionally not copied into the repository because they contain absolute
workstation links and assertions that became stale during remediation.

- Baseline report SHA-256: `ad6d666cf119ab84bde74332e643eb7a1fdab56b06aaca7ca4aec6152a03a400`
- Remediation work-order SHA-256: `058d1f45cb6bd772f55c0c43d2157aaaaa9826d0c28ea9adc8de97c0a5002995`

This document contains no source-customer identity or private contact data. It
records repository disposition only and is not evidence of production
readiness.

## Remediation disposition

The standalone repository baseline starts at commit `0725a27`. The audited
task sequence runs through commit `2da4238`.

| Disposition | Tasks | Result |
| --- | --- | --- |
| Implemented in isolated commits | T-01–T-16 and T-19–T-29 | Each concern has a dedicated signed-off commit and the static quality gates passed after it. |
| Skipped because tracked evidence did not reproduce | T-17 | The two cited Python cache directories were ignored and untracked. They were removed locally and remained absent after the quality gate, so no source diff was appropriate. |
| Blocked by the work-order rule | T-18 | The local `development/.env` is ignored publication-excluded state and the work order explicitly prohibited changing it. |

## Superseded source-report claims

The older full-audit statements below are not current facts:

- Git is initialized on `main`, and forbidden local paths are checked against
  tracked files.
- `development/.env` and `development/frappe-bench/` are ignored and are not
  tracked publication sources.
- The repository license is `AGPL-3.0-only`; app and service metadata are
  reconciled and contributions use DCO sign-off.
- Control-plane HTTP security, OpenAPI drift, AI Proposal requester isolation,
  and Service Location behavior now have dedicated tests.
- The observability directory contains documented signals and non-secret alert
  examples, including a p95 latency alert.
- Backup/restore and incident-response runbooks exist.

## Verification state

- `scripts/run-quality-gates.sh`: passed on the remediated tree.
- `scripts/dev.sh compose-config`: passed after the Compose changes.
- Ruff 0.14.10 (`ruff check --no-cache apps/ services/`): passed before the
  lint CI commit; later commits did not change Python source.
- Publication secret scanning: passed, including a repository-wide scan for
  unrelated customer-project names.
- Current Docker-backed control-plane, contract, core-app, and service-app test
  reruns remain required before release. Earlier runs passed, but later commits
  added tests and runtime metadata, so those earlier results are not treated as
  current evidence.

## Remaining owner/external gates

- Choose a concrete private vulnerability-reporting channel for `SECURITY.md`.
- A real model-provider adapter remains an explicit product decision; the
  development template must continue to fail closed for other providers.
- Create the target private GitHub repository, push `main`, and confirm all
  required status checks on the pushed commit.
- Run the full Docker-backed verification matrix and a fresh-clone demo before
  any public release or production-readiness claim.
