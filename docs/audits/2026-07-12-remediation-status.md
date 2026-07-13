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
task sequence runs through commit `2da4238`; the T-09 runtime correction is in
commit `4087616`.

| Task | Status | Commit | Acceptance evidence |
| --- | --- | --- | --- |
| T-01 | Complete | `fa19896` | Repository structure and forbidden-path gates pass. |
| T-02 | Complete | `2729151` | CI workflow and Python lint gates pass. |
| T-03 | Complete | `bfb8a99` | Control-plane bearer-token and fail-closed tests pass. |
| T-04 | Complete | `3d82d43` | The non-root control-plane container starts healthy. |
| T-05 | Complete | `5028936` | Published OpenAPI responses pass contract tests. |
| T-06 | Complete | `682f41a` | Exact route/response drift tests pass; the dummy-route negative probe fails as intended. |
| T-07 | Complete | `41a12e6` | Authorization matrix and tenant-isolation gates pass. |
| T-08 | Complete | `010473e` | Backlog and first-public-issue metadata reconcile. |
| T-09 | Complete | `81a68d3`, `4087616` | Query filtering and direct permission checks pass in the Docker core integration suite. |
| T-10 | Complete | `e4588b1` | Full service integration suite passes 8 tests. |
| T-11 | Complete | `8d88dfa` | Pinned upstream overrides render through Compose. |
| T-12 | Complete | `b680c7b` | Redis health checks and restart policies pass Compose validation. |
| T-13 | Complete | `4a6eced` | Structure gate passes; the unexpected-root negative probe fails as intended. |
| T-14 | Complete | `79929ac` | Dependency-update policy gate passes. |
| T-15 | Complete | `5176840` | Upstream-upgrade readiness gate passes. |
| T-16 | Complete | `feece53` | Release policy and readiness-manifest gates pass. |
| T-17 | Skipped | — | Cited cache directories were ignored and untracked; removal produced no source diff. |
| T-18 | Blocked by work order | — | `development/.env` is ignored, publication-excluded local state that the work order prohibited changing. |
| T-19 | Complete | `627e1e2` | License metadata reconciles as `AGPL-3.0-only`. |
| T-20 | Complete | `2ff0504` | Industry-pack manifest gate passes. |
| T-21 | Complete | `ec4ea5e` | Industry-pack lifecycle gate passes. |
| T-22 | Complete | `e3ed9e6` | AI data-boundary gate passes. |
| T-23 | Complete | `f164971` | AI workflow registry gate passes. |
| T-24 | Complete | `892bb49` | Transaction-safety gate passes. |
| T-25 | Complete | `a0aa1af` | Compose renders with documented environment inputs. |
| T-26 | Complete | `248633e` | Backup/restore runbook is covered by operations-readiness checks. |
| T-27 | Complete | `d9045f9` | Incident-response runbook is covered by operations-readiness checks. |
| T-28 | Complete | `e9a7a87` | Observability-readiness gate passes. |
| T-29 | Complete | `2da4238` | Frappe p95 latency alert example passes observability checks. |

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

Verified on the remediated tree on 2026-07-13:

- `scripts/run-quality-gates.sh`: passed.
- Docker-backed control-plane suite: 7 tests passed.
- Docker-backed contract suite: 11 tests passed.
- Docker-backed core integration suite: 1 test passed.
- Docker-backed service integration suite: 8 tests passed.
- Frappe migration and synthetic demo seeding: passed.
- Compose rendering: passed; the control-plane container reported healthy.
- Publication scanning: passed, including the repository-wide unrelated-name
  scan.
- The private GitHub repository, protected `main`, Dependabot settings, and
  private vulnerability-reporting form were verified. Required checks passed
  for the remediation code merged through `4087616`.

## Remaining product decision

A real model-provider adapter remains an explicit product decision. The
development template continues to fail closed for unapproved providers, and no
provider choice is required to close this remediation work order.
