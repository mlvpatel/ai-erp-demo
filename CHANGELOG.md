# Changelog

This project follows a simple changelog format until the first public release.
Dates use `YYYY-MM-DD`.

## Unreleased

- Created the AI ERP Demo repository structure for a Frappe/ERPNext-based,
  AI-assisted ERP product.
- Added repo-local delivery skills and working rules for ERP safety,
  minimal-change implementation, and AI approval boundaries.
- Added the first service-operations industry pack with work-order, closeout,
  parts, invoice-readiness, profitability, and AI proposal workflow checks.
- Added a draft-only FastAPI AI control plane with a versioned OpenAPI contract.
- Added reproducible local development configuration, Docker Compose, demo seed,
  and quality-gate scripts.
- Added discovery, design, architecture, security, publication, and local demo
  documentation.

## Release policy

No public release should be tagged until the root `LICENSE` decision is complete,
`scripts/check-open-source-ready.sh --release` passes, GitHub CI passes, and a
fresh clone can complete the local demo runbook.
The detailed versioning and release checklist lives in
`docs/workflows/release-process.md` and is validated by
`python3 scripts/check-release-policy.py`.
