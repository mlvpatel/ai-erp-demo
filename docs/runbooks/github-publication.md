# GitHub publication runbook

Use this checklist before turning the local `ERP demo` folder into the public
open-source repository. The goal is a clean first impression: no secrets, no
vendored upstream ERPNext checkout, reproducible development pins, and clear
AI safety boundaries.

## 1. Resolve owner decisions

- Confirm the selected AGPL-3.0-only policy remains consistent across the root,
  apps, service, and contribution policy.
  - ADR-0005 records the accepted decision.
  - Use `docs/runbooks/license-decision.md` for any future policy change.
  - Optionally copy `config/owner-decisions.example.json` to ignored
    `config/owner-decisions.local.json` and validate it with
    `python3 scripts/check-owner-decisions.py --strict` before editing public
    license/contact files.
- Choose the public repository name, default branch, and owner organization.
- Decide whether the first public release is a source-only developer demo or a
  tagged runnable preview.
- Name the initial maintainer or maintainer group before accepting external
  contributions.
- Review `docs/product/public-positioning.md` and `ROADMAP.md` so the repository
  does not over-claim production readiness or all-industry coverage.
- Review `docs/product/requirements-traceability.md` so publication claims map
  to current evidence.
- Review `BACKLOG.md` and convert only license-safe, low-risk items into first
  GitHub issues.
- Review `config/first-public-issues.json` for the launch issue seed list and
  keep it aligned with `BACKLOG.md`.
- Review `.github/labels.json` so public issue labels match the safety and
  triage workflow before enabling community issues.
- Review `.github/repository-metadata.json` so the public description, topics,
  feature flags, branch protection target, and required checks match the current
  positioning.
- Review `config/ci-workflow.json` so required GitHub status checks still match
  the actual CI workflow jobs and commands.
- Review `config/release-readiness.json` so the public-release blocker map
  matches this runbook, requirements traceability, and GitHub metadata.
- Review `config/release-policy.json` and
  `docs/workflows/release-process.md` so version tags, release commands, and
  pre-1.0 public claims stay aligned.
- Review `config/integration-safety.json` so future connector boundaries remain
  contract-first, notification-only, idempotent, and free of customer payloads.
- Review `config/operations-readiness.json` so backup/restore runbooks,
  incident response, publication exclusions, and release checks stay aligned.
- Review `config/observability-readiness.json` so monitoring guidance, safe
  alert examples, telemetry data boundaries, and incident links stay aligned.
- Review `config/performance-readiness.json` so load-profile examples,
  record-volume assumptions, performance evidence rules, and release checks
  stay aligned.
- Review `config/upstream-upgrade-readiness.json` so Frappe/ERPNext pin
  changes, image digest changes, bootstrap safeguards, and validation commands
  stay aligned.
- Review `config/license-metadata.json` before applying the chosen license so
  all public license/contact metadata targets are reconciled together.
- Review `config/fresh-clone-demo.json` so the local demo runbook, helper
  commands, tracked env example, and Compose service map stay aligned.
- Review `config/demo-script.json` and `docs/runbooks/demo-script.md` before
  adding README screenshots, GIFs, or public demo walkthrough issues.
- Review `config/ai-data-boundary.json` so the MVP AI workflow still sends only
  allow-listed operational fields to the control plane.
- Review `config/migration-safety.json` so Frappe app metadata, DocTypes,
  fixtures, empty patch files, and the demo migration order remain aligned.
- Review `config/publication-secret-scan.json` so secret patterns, synthetic
  email domains, local-only path exclusions, and required safety docs still
  match the repository.

## 2. Clean local state

- Never publish:
  - `development/.env`
  - `development/frappe-bench/`
  - `config/owner-decisions.local.json`
  - `sites/`, `logs/`, database dumps, backups, private files, or generated
    assets
  - `*.sql`, `*.sql.gz`, `*.dump`, `*.backup`, `*-files.tar`, or
    `*-private-files.tar`
  - API keys, model keys, customer data, or private prompts
- Keep upstream Frappe and ERPNext as cloned development dependencies only.
  Do not copy upstream source into the root repository history.
- Confirm `.gitignore` still excludes local Frappe Bench state before the first
  commit.
- Confirm `.gitattributes` still marks local-only paths as `export-ignore`
  before publishing a Git-generated source archive.
- Run `scripts/local-artifacts.sh --check` before publishing a source archive.
  If it reports only generated cache/build files, review the list and run
  `scripts/local-artifacts.sh --clean`.
- Run `scripts/check-publication-source.sh --strict` before publishing a manual
  source archive.
- Run `python3 scripts/check-publication-secrets.py` before publishing or after
  changing fixtures, examples, issue templates, or publication/security docs.

## 3. Run pre-publication checks

From the repository root:

```bash
scripts/run-quality-gates.sh
scripts/check-publication-source.sh --strict
python3 scripts/check-publication-secrets.py
python3 scripts/check-operations-readiness.py
python3 scripts/check-observability-readiness.py
python3 scripts/check-performance-readiness.py
python3 scripts/check-doc-links.py
python3 scripts/check-ai-data-boundary.py
python3 scripts/check-integration-safety.py
python3 scripts/check-migration-safety.py
python3 scripts/check-dependency-updates.py
python3 scripts/check-upstream-upgrade-readiness.py
python3 scripts/check-github-metadata.py
python3 scripts/check-ci-workflow.py
python3 scripts/check-github-labels.py
python3 scripts/check-first-public-issues.py
python3 scripts/check-fresh-clone-demo.py
python3 scripts/check-demo-script.py
python3 scripts/check-release-readiness.py
python3 scripts/check-release-policy.py
python3 scripts/check-owner-decisions.py
python3 scripts/check-license-metadata.py
python3 scripts/check-public-claims.py
python -m pip install ./services/ai_control_plane
python -m unittest discover -s services/ai_control_plane/tests -v
python -m unittest discover -s tests/contract -v
```

For the local Frappe integration stack:

```bash
cp development/.env.example /tmp/ai-erp-ci.env
docker compose --env-file /tmp/ai-erp-ci.env -f infra/compose/docker-compose.dev.yml config --quiet
docker compose --env-file development/.env -f infra/compose/docker-compose.dev.yml exec --workdir /workspace/development/frappe-bench frappe bench --site ai-erp.localhost run-tests --app ai_erp_service --test-category integration --failfast
```

## 4. Initialize and push

- Initialize the root Git repository only after the license decision is made.
- Commit only the project root files, not ignored development checkouts.
- Use a signed or clearly attributable first commit when possible.
- Push to a private GitHub repository first and verify the file list in the
  browser before making it public.

## 5. Configure GitHub

- Enable branch protection for `main`.
- Require CI for pull requests.
- Restrict force-pushes on protected branches.
- Use `.github/repository-metadata.json` as the setup checklist for default
  branch, topics, feature flags, and required status checks.
- Enable Dependabot alerts. Do not auto-merge dependency changes that alter
  Frappe/ERPNext pins, image digests, or ERP transaction logic.
- Review `docs/workflows/dependency-updates.md` before enabling automated
  dependency pull requests.
- Review `config/dependency-updates.json` so Dependabot labels and monitored
  directories stay aligned with the manual-only ERP runtime pin policy.
- Create or sync labels from `.github/labels.json` before opening the first
  public issues. Keep `erp-safety`, `ai-safety`, and `blocked-license` visible.
- Create first public issues from `config/first-public-issues.json` only after
  the root license and release-readiness gates are resolved.
- Confirm `SECURITY.md` is visible on the repository security tab.
- Open the private reporting URL in `SECURITY.md` while signed in and confirm it
  resolves to the `mlvpatel/ai-erp-demo` Security Advisory form, not a
  placeholder repository or a public issue form.
- Confirm `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `GOVERNANCE.md`,
  `SUPPORT.md`, and `CHANGELOG.md` are visible from the repository landing page
  or linked documentation.
- Add repository topics only after the public positioning is settled, for
  example `erpnext`, `frappe`, `erp`, `ai`, `field-service`, and `open-source`.

### Manual release-time evidence

The `python3 scripts/check-owner-decisions.py --strict` and
`python3 scripts/check-license-metadata.py --strict` checks are manual
release-time gates. They require the maintainer-controlled, ignored owner
decision file and a deliberate review of public license/contact metadata, so
ordinary CI must not fabricate or publish that owner evidence. The
`github-ci-passes` blocker is also manual and release-time-only because a local
checkout cannot prove the required GitHub Actions checks passed on the exact
target commit; confirm those checks in the target repository before tagging.

## 6. First public release gate

Do not tag a release until:

- The root `LICENSE` exists and matches ADR-0005's resolved decision.
- Generated app and Python package license/contact metadata no longer contain
  scaffold placeholders.
- Local generated artifacts have been cleaned or excluded from the publication
  artifact.
- `scripts/check-open-source-ready.sh --release` passes.
- `python3 scripts/check-release-readiness.py --strict` passes for local
  release blockers.
- `python3 scripts/check-publication-secrets.py` passes for publishable sources.
- `python3 scripts/check-operations-readiness.py` passes for recovery and
  incident-response guardrails.
- `python3 scripts/check-observability-readiness.py` passes for monitoring,
  alerting, and telemetry-data-boundary guardrails.
- `python3 scripts/check-performance-readiness.py` passes for performance
  profile and scalability-claim guardrails.
- If used, `config/owner-decisions.local.json` passes
  `python3 scripts/check-owner-decisions.py --strict`.
- `python3 scripts/check-license-metadata.py --strict` passes after public
  license/contact files are reconciled.
- The README describes the current runnable path truthfully.
- The public roadmap and positioning describe implemented service-operations
  scope separately from future industry packs.
- Requirements traceability still marks public release blockers honestly.
- The first issue backlog avoids unsafe starter tasks that touch ERP posting,
  AI approval bypasses, permissions, payroll, or compliance.
- CI passes on GitHub.
- A fresh clone can bootstrap the dev stack using `development/README.md`.
- `python3 scripts/check-fresh-clone-demo.py` passes for runbook/helper
  consistency.
- `python3 scripts/check-demo-script.py` passes before README media or public
  demo walkthrough issues are published.
- `python3 scripts/check-migration-safety.py` passes for Frappe migration
  metadata and helper/runbook order.
- `python3 scripts/check-upstream-upgrade-readiness.py` passes for
  Frappe/ERPNext pin and runtime image upgrade guardrails.
- `python3 scripts/check-integration-safety.py` passes for connector
  reservation state and business-event safety.
- The local demo runbook in `docs/runbooks/local-demo.md` is still accurate.
- The service industry workflow has a passing integration check.
- The AI control plane remains draft-only and cannot directly post financial,
  stock, payroll, access-control, or compliance changes.
