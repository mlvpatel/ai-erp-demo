# Checked-in configuration

Keep only non-secret defaults and schema examples here. Environment-specific
secrets belong in the deployment platform or a secrets manager.

- `industry-packs.json`: machine-readable industry-pack roadmap. It records
  which packs are implemented, reserved, or only planned so public claims stay
  aligned with the actual repository state.
- `industry-pack-lifecycle.json`: machine-readable industry expansion workflow.
  It keeps planned, reserved, and implemented pack status rules aligned with the
  roadmap, design template, and reserved app folders.
- `repository-structure.json`: machine-readable layout contract. It keeps the
  repo organized around Frappe apps, AI control-plane services, contracts,
  docs, infra, tests, and scripts instead of generic frontend/backend folders.
- `contract-lifecycle.json`: machine-readable contract versioning workflow. It
  keeps OpenAPI and business-event IDs, filenames, versions, status rules, docs,
  and safety boundaries aligned.
- `integration-safety.json`: machine-readable connector and business-event
  guardrail. It keeps the connector app reserved, business events
  notification-only, and future adapter boundaries contract-first.
- `operations-readiness.json`: machine-readable recovery and incident-response
  guardrail. It keeps backup/restore runbooks, incident handling, publication
  exclusions, support/security docs, and release checks aligned.
- `observability-readiness.json`: machine-readable monitoring and alerting
  guardrail. It keeps public observability guidance, safe example alerts,
  telemetry data boundaries, incident runbooks, and release checks aligned.
- `performance-readiness.json`: machine-readable performance guardrail. It
  keeps load-profile examples, record-volume targets, safety invariants,
  workflow docs, and release checks aligned.
- `first-public-issues.json`: launch-safe GitHub issue seed list. It keeps
  early public issues small, license-gated, and away from ERP/AI safety
  boundaries.
- `mvp-acceptance.json`: machine-readable MVP acceptance map. It ties the
  acceptance metrics in `docs/product/mvp-scope.md` to evidence files, anchors,
  safety boundaries, and runnable verification commands.
- `authorization-matrix.json`: machine-readable role/action guardrail map. It
  keeps role fixtures, DocType permissions, permission hooks, sensitive action
  guards, docs, and tests aligned.
- `transaction-safety.json`: machine-readable ERP transaction invariant map. It
  keeps stock issue, draft invoice, billing immutability, invoice-readiness,
  AI-review side-effect, and demo-seed safety evidence aligned.
- `audit-evidence.json`: machine-readable audit evidence contract. It keeps AI
  Proposal ledger fields, source hashes, review metadata, deterministic ERP
  record links, tests, and safety documentation aligned.
- `fresh-clone-demo.json`: machine-readable local demo runbook contract. It
  keeps first-run commands, tracked env requirements, Compose services, and demo
  safety warnings aligned. It also defines the `demo-info` output-safety
  contract so local paths and secret-like env assignments stay out of helper
  output.
- `demo-script.json`: machine-readable public demo script contract. It keeps
  the README/demo walkthrough story aligned with MVP claims, local demo
  commands, screenshot safety rules, and first-public issue planning.
- `release-readiness.json`: machine-readable public-release blocker map. It
  keeps GitHub metadata, publication runbooks, traceability docs, and strict
  local checks aligned while owner/external release decisions are still pending.
- `release-policy.json`: machine-readable versioning and release process map.
  It keeps the release workflow, changelog policy, pre-1.0 claims, and release
  blocker manifest aligned.
- `owner-decisions.example.json`: safe template for owner-level publication
  decisions. Copy it to ignored `config/owner-decisions.local.json` when the
  owner is ready to choose license, public contact, repository owner/name,
  release type, and contribution policy.
- `license-metadata.json`: machine-readable license/contact reconciliation
  target map. It records which public files must be updated together after the
  owner chooses a license policy.
- `ci-workflow.json`: machine-readable GitHub Actions contract. It keeps the
  required status checks, workflow job names, and release-safe CI commands in
  sync.
- `ai-data-boundary.json`: machine-readable AI sharing boundary for the MVP
  closeout-summary workflow. It keeps payload fields, strict models, contracts,
  tests, and safety docs aligned.
- `ai-workflow-registry.json`: machine-readable registry of approved AI
  workflows. It keeps AI routes, proposal types, draft-only policy, data
  boundaries, docs, and tests aligned before future AI features are added.
- `tenant-isolation.json`: machine-readable site/tenant guardrail. It keeps
  the one-Frappe-site-per-tenant ADR aligned with AI payloads, contracts, event
  envelopes, source-code shortcuts, and safety docs.
- `migration-safety.json`: machine-readable Frappe migration guardrail. It
  keeps DocType JSON, fixtures, empty patch files, demo migration order, and
  no-direct-DDL rules aligned.
- `dependency-updates.json`: machine-readable Dependabot and manual-update
  policy. It keeps automated dependency visibility narrow and ERP runtime pins
  manual-only.
- `upstream-upgrade-readiness.json`: machine-readable Frappe/ERPNext upgrade
  guardrail. It keeps upstream pin rules, bootstrap safety, validation
  commands, migration docs, and release checks aligned.
- `publication-secret-scan.json`: machine-readable publication safety scan. It
  keeps secret patterns, allowed synthetic domains, local-only exclusions, and
  required safety docs aligned.

GitHub-facing repository metadata lives under `.github/` because it is part of
the public repository setup rather than runtime configuration.
