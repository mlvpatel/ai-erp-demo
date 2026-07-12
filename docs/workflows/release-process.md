# Release process

Use this workflow before tagging a public release or publishing a GitHub source
archive. The project is pre-1.0 until the owner resolves licensing and a fresh
clone proves the local demo path.

## Versioning

- Use SemVer-style tags: `vMAJOR.MINOR.PATCH`.
- Use `v0.x.y` for developer previews before production readiness is proven.
- Do not tag `v1.0.0` until a future ADR accepts production-readiness criteria,
  upgrade policy, backup/restore expectations, and support ownership.
- Keep `CHANGELOG.md` under `## Unreleased` until the release commit is ready.
- Move released notes into a dated version section during the release commit.

## Public-release gate

Do not tag a public release until:

1. The root `LICENSE` is selected and committed.
2. Generated app license/contact metadata is reconciled.
3. `scripts/check-open-source-ready.sh --release` passes.
4. `python3 scripts/check-release-readiness.py --strict` passes.
5. `python3 scripts/check-publication-secrets.py` passes.
6. `python3 scripts/check-upstream-upgrade-readiness.py` passes.
7. `python3 scripts/check-operations-readiness.py` passes.
8. `python3 scripts/check-observability-readiness.py` passes.
9. `python3 scripts/check-performance-readiness.py` passes.
10. `python3 scripts/check-license-metadata.py --strict` passes.
11. `python3 scripts/check-owner-decisions.py --strict` passes if
   `config/owner-decisions.local.json` is used.
12. `scripts/run-quality-gates.sh` passes.
13. GitHub CI passes in the target repository.
14. A fresh clone can bootstrap the local demo runbook.

## Release packaging rules

- Publish from the root repository only; never include `development/frappe-bench/`
  or other local Frappe/ERPNext checkouts.
- Do not include `.env`, local secrets, customer exports, production backups,
  private prompts, logs, generated sites, database dumps, or backup artifacts.
- Run `scripts/check-publication-source.sh --strict` before creating a manual
  source archive.
- Verify `config/publication-secret-scan.json` when adding new file types,
  fixtures, examples, or issue templates.

## Claims allowed before 1.0

Before 1.0, describe the project as:

- an AI-assisted ERP demo and starter,
- built on ERPNext/Frappe,
- implementing a service-operations workflow,
- using human approval for consequential actions,
- not production-ready.

Do not claim autonomous ERP posting, autonomous customer messaging, final
open-source licensing, production readiness, or broad all-industry coverage
until the relevant implementation, release, and owner gates prove those claims.
