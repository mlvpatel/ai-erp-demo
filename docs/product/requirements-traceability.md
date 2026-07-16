# Requirements traceability

This matrix maps the original project request to repository evidence. Use it
before claiming the goal is complete, preparing a GitHub release, or deciding
the next build step.

Repository-owned code is licensed under AGPL-3.0-only. License and contact
metadata is reconciled across the custom apps and AI control plane. The private
repository and zero-cost local synthetic demo branch exist. The demo is
separate from the deferred production pilot, which still requires protected
deployment evidence, human approval, and legal review.

## Status key

- **Implemented**: artifact exists and has a matching verification path.
- **Prepared**: repository support exists, but an owner/external decision or
  public GitHub state is still required.
- **Blocked**: cannot be completed safely without an owner decision.

## Original request traceability

| Requirement | Current status | Evidence | Verification |
| --- | --- | --- | --- |
| Create `ERP demo` folder. | Implemented | Repository root and root `README.md`. | Inspect the local folder and run `scripts/run-quality-gates.sh` from the root. |
| Create an ERP-specific folder structure, not a generic project structure. | Implemented | `README.md` layout, `config/repository-structure.json`, `docs/architecture/system-context-and-repository-map.md`, `docs/architecture/system-boundaries.md`, `docs/architecture/domain-data-model.md`, `apps/`, `services/`, `contracts/`, `infra/`, `tests/`. | `scripts/check-repository-structure.py` verifies required ERP-specific folders, implemented app markers, reserved app boundaries, and forbidden generic root directories. |
| Prepare for an open-source GitHub repo. | Prepared | `.github/`, `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `GOVERNANCE.md`, `SECURITY.md`, `SUPPORT.md`, `CHANGELOG.md`, `BACKLOG.md`, `config/first-public-issues.json`, `config/release-readiness.json`, `config/release-policy.json`, `config/license-metadata.json`, `config/publication-secret-scan.json`, `docs/runbooks/github-publication.md`, `docs/workflows/release-process.md`. | `scripts/check-open-source-ready.sh` passes in normal mode. Release mode remains blocked until repository, CI, fresh-clone, security-contact, and local-publication gates pass. |
| Decide the July 2026 tech stack and explain why. | Implemented | `docs/architecture/tech-stack-2026-07.md`, `docs/adr/0001-adopt-erpnext-frappe-core.md`. | Review the stack doc and ADR. `scripts/check-reproducibility.sh` verifies pinned development defaults. |
| Scan leading open-source ERP GitHub repositories. | Implemented | `docs/discovery/open-source-erp-scan-2026-07.md`. | Review the scan sources and decision impact section. Refresh the scan before a dated public claim. |
| Provide a discovery-to-design plan. | Implemented | `docs/discovery/discovery-design-plan.md`, `docs/discovery/service-operations-interview-guide.md`, `docs/product/industry-pack-design-template.md`. | Review discovery phase gates and use the interview guide before changing MVP scope. |
| Incorporate the supplied MVP blueprint. | Implemented | `docs/discovery/mvp-blueprint-review.md`, `docs/product/mvp-scope.md`, `ROADMAP.md`. | Confirm the review maps blueprint recommendations to adopted, adjusted, rejected, and deferred project decisions. |
| Document repeatable delivery and review workflows. | Implemented | `docs/workflows/quality-gates.md`, `CONTRIBUTING.md`, `GOVERNANCE.md`. | Contribution guidance requires reading the boundary and gate documentation before ERP feature or delivery work. |
| Apply a minimal-change engineering discipline. | Implemented | `docs/workflows/quality-gates.md`, `CONTRIBUTING.md`. | Review guidance requires the smallest correct change and forbids simplifying away validation, security, audit, or accessibility. |
| Build an AI ERP system for broad industry expansion. | Prepared | `apps/ai_erp_core/`, first vertical `apps/ai_erp_service/`, reserved future packs, `config/industry-packs.json`, `config/industry-pack-lifecycle.json`, `docs/product/industry-pack-roadmap.md`, `docs/workflows/industry-pack-lifecycle.md`, `docs/product/public-positioning.md`. | Current implementation proves service operations. `scripts/check-industry-pack-manifest.py` verifies the implemented/reserved/planned pack map. `scripts/check-industry-pack-lifecycle.py` verifies the planned → reserved → implemented lifecycle. Broad industry coverage is roadmap-driven, not yet claimed as implemented. |
| Keep AI safe and governed. | Implemented for MVP | `config/ai-data-boundary.json`, `config/ai-workflow-registry.json`, `docs/workflows/ai-workflow-lifecycle.md`, `docs/adr/0003-ai-proposes-erp-validates.md`, `docs/adr/0004-stateless-ai-control-plane-and-proposal-ledger.md`, `docs/security/threat-model.md`, `docs/security/ai-workflow-review.md`, `docs/architecture/domain-data-model.md`, negative unsupported-action tests, `services/ai_control_plane/`, `apps/ai_erp_core/`. | `python3 scripts/check-ai-data-boundary.py`; `python3 scripts/check-ai-workflow-registry.py`; `scripts/dev.sh control-plane-test`, `scripts/dev.sh contract-test`, and `scripts/dev.sh service-test`. |
| Preserve tenant/site isolation boundaries. | Implemented for MVP | `docs/adr/0002-tenant-isolation-by-frappe-site.md`, `config/tenant-isolation.json`, `docs/workflows/tenant-isolation.md`, AI control-plane request model, OpenAPI contract, service events, and payload builder. | `python3 scripts/check-tenant-isolation.py`; `scripts/run-quality-gates.sh` |
| Preserve Frappe-native migration safety. | Implemented for MVP | `config/migration-safety.json`, `docs/workflows/migration-safety.md`, app DocType JSON, fixtures, empty patch files, bootstrap script, local demo runbook, and `scripts/dev.sh migrate`. | `python3 scripts/check-migration-safety.py`; `scripts/run-quality-gates.sh` |
| Define upstream ERPNext/Frappe upgrade boundaries. | Implemented for pre-production readiness | `config/upstream-upgrade-readiness.json`, `docs/workflows/upstream-upgrade-readiness.md`, `docs/workflows/dependency-updates.md`, `development/README.md`, bootstrap pin safeguards, reproducibility checks. | `python3 scripts/check-upstream-upgrade-readiness.py`; `scripts/run-quality-gates.sh` |
| Preserve ERP authorization and approval boundaries. | Implemented for MVP | `config/authorization-matrix.json`, `docs/workflows/authorization-and-approvals.md`, `docs/workflows/service-operations.md`, role fixtures, DocType permissions, permission hooks, service workflow tests. | `python3 scripts/check-authorization-matrix.py`; `scripts/dev.sh service-test` |
| Preserve ERP transaction safety invariants. | Implemented for MVP | `config/transaction-safety.json`, `docs/workflows/transaction-safety.md`, service work-order controller, AI Proposal controller, service workflow tests, `config/mvp-acceptance.json`. | `python3 scripts/check-transaction-safety.py`; `scripts/dev.sh service-test` |
| Preserve audit evidence for AI-supported ERP actions. | Implemented for MVP | `config/audit-evidence.json`, `docs/workflows/audit-evidence.md`, AI Proposal and AI Proposal Source DocTypes, Service Work Order transaction links, service workflow tests. | `python3 scripts/check-audit-evidence.py`; `scripts/dev.sh service-test` |
| Keep publishable sources free of secrets and customer data. | Implemented | `config/publication-secret-scan.json`, `scripts/check-publication-secrets.py`, `docs/security/data-classification.md`, `docs/runbooks/github-publication.md`, `.github/` templates. | `python3 scripts/check-publication-secrets.py`; `scripts/run-quality-gates.sh` |
| Provide a runnable local demo path. | Implemented | `development/README.md`, `infra/compose/docker-compose.dev.yml`, `scripts/dev.sh`, `config/fresh-clone-demo.json`, `docs/runbooks/local-demo.md`, service demo seed. | On a prepared Docker stack, run `scripts/dev.sh demo-check`. Locally, run `python3 scripts/check-fresh-clone-demo.py` to verify runbook/helper consistency. |
| Prepare a truthful public demo walkthrough. | Implemented | `docs/runbooks/demo-script.md`, `config/demo-script.json`, README demo links and synthetic screenshots, first-public demo issue manifest, MVP acceptance map. | `python3 scripts/check-demo-script.py`; `scripts/run-quality-gates.sh`; screenshots are replaced only after `scripts/dev.sh demo-check` passes. |
| Create GitHub CI and automation. | Implemented; current branch result must be revalidated | `.github/workflows/ci.yml`, production image/deploy/restore/capacity workflows, `.github/dependabot.yml`, and checked-in workflow policy. | Run the local gates, then require all protected GitHub checks on the current commit; older successful runs are not evidence for new changes. |
| Define public release/versioning policy. | Implemented | `docs/workflows/release-process.md`, `config/release-policy.json`, `CHANGELOG.md`, `config/release-readiness.json`. | `python3 scripts/check-release-policy.py`; `scripts/run-quality-gates.sh` |
| Version public APIs and business events. | Implemented for MVP boundaries | `contracts/catalog.json`, `config/contract-lifecycle.json`, `docs/workflows/contract-lifecycle.md`, `contracts/openapi/ai-control-plane-v1.yaml`, `contracts/events/service-operations-v1.yaml`, contract tests. | `scripts/check-contract-catalog.py`; `scripts/check-contract-lifecycle.py`; `scripts/dev.sh contract-test` |
| Keep future integrations contract-first and safe. | Implemented for MVP boundaries | `config/integration-safety.json`, `docs/workflows/integration-safety.md`, reserved `apps/ai_erp_connectors/`, business-event contract, contract catalog, event contract tests, connector README. | `python3 scripts/check-integration-safety.py`; `scripts/run-quality-gates.sh` |
| Define backup, restore, and incident-response boundaries. | Implemented for pre-production readiness | `config/operations-readiness.json`, `docs/workflows/operations-readiness.md`, `docs/runbooks/backup-restore.md`, `docs/runbooks/incident-response.md`, publication source and secret-scan guardrails. | `python3 scripts/check-operations-readiness.py`; `scripts/run-quality-gates.sh` |
| Define observability and alerting boundaries. | Implemented for pre-production readiness | `config/observability-readiness.json`, `docs/workflows/observability-readiness.md`, `infra/observability/README.md`, `infra/observability/alert-rules.example.yml`, incident and data-classification docs. | `python3 scripts/check-observability-readiness.py`; `scripts/run-quality-gates.sh` |
| Define performance and scalability boundaries. | Implemented for pre-production readiness | `config/performance-readiness.json`, `docs/workflows/performance-readiness.md`, `tests/performance/README.md`, `tests/performance/service-operations-load-profile.example.json`, quality-gate docs. | `python3 scripts/check-performance-readiness.py`; `scripts/run-quality-gates.sh` |
| Rehearse the service pilot without overstating acceptance. | Code-level remediation implemented; production evidence and human gates pending | `config/pilot-readiness.json`, browser/integration suites, protected AWS workflows, `docs/runbooks/service-operations-synthetic-uat.md`, `docs/compliance/service-operations-pilot-evidence-template.md`. | `python3 scripts/check-pilot-readiness.py`; AWS activation, live OpenAI, exact capacity, recovery/deletion/rollback evidence, legal, human UAT, support-owner, and go/no-go remain pending. |
| Keep local generated artifacts out of publication. | Prepared | `.gitignore`, `.gitattributes`, `scripts/local-artifacts.sh`, `scripts/check-publication-source.sh`, `docs/runbooks/github-publication.md`. | `scripts/local-artifacts.sh --check`; `scripts/check-publication-source.sh --strict`; strict release mode fails while artifacts remain. |
| Publish publicly on GitHub. | Blocked | `docs/runbooks/github-publication.md`, `config/release-readiness.json`, `config/publication-secret-scan.json`, `.github/repository-metadata.json`. | `scripts/check-open-source-ready.sh --release` must pass after repository state, CI, fresh-clone, security-contact, and local-publication gates are resolved. |

## MVP acceptance evidence

| MVP claim | Evidence | Verification command |
| --- | --- | --- |
| Technician and manager roles are separated. | `config/mvp-acceptance.json`, `docs/workflows/service-operations.md`, service integration tests. | `scripts/dev.sh service-test`; `python3 scripts/check-mvp-acceptance.py` |
| Work order closeout and exceptions gate invoice readiness. | `config/mvp-acceptance.json`, `apps/ai_erp_service/`, service workflow tests. | `scripts/dev.sh service-test`; `python3 scripts/check-mvp-acceptance.py` |
| Parts issue is manager-triggered and idempotent. | Service workflow tests and README. | `scripts/dev.sh service-test` |
| Draft Sales Invoice is finance-triggered, draft-only, and idempotent. | `config/mvp-acceptance.json`, service workflow tests and README. | `scripts/dev.sh service-test`; `python3 scripts/check-mvp-acceptance.py` |
| AI closeout draft is cited, immutable, review-only, and has no ERP side effect. | `config/mvp-acceptance.json`, `ai_erp_core` proposal model, AI control-plane tests, service workflow tests. | `scripts/dev.sh control-plane-test`; `scripts/dev.sh contract-test`; `scripts/dev.sh service-test`; `python3 scripts/check-mvp-acceptance.py` |
| Demo seed is synthetic and idempotent. | `ai_erp_service.demo_seed.seed_service_demo`; local demo runbook. | `scripts/dev.sh seed-demo`; `scripts/dev.sh demo-check` |
| Demo guidance is discoverable from the CLI. | `scripts/dev.sh demo-info`; local demo runbook. | `scripts/dev.sh demo-info` |

## Completion blockers

The repository must not be marked production-pilot approved until:

1. The current commit passes every local and protected GitHub check. GitHub CI
   passes in the actual target repository.
2. Local generated artifacts are cleaned or excluded from the publication
   artifact. A root Git repository is initialized and checked for forbidden
   tracked paths. A fresh clone verifies the local demo runbook.
3. Protected deployment, live AI evaluation, exact capacity, recovery, deletion,
   and rollback drills produce reviewed evidence.
4. Human UAT, design-partner validation, legal review, support ownership, and
   accountable go/no-go are signed.

The zero-cost local synthetic demo may be released when its clean-checkout,
Docker, media-safety, and private GitHub gates pass. The separately deferred
field-service production pilot remains unapproved, with two standard ERPNext
configured demos and no broad all-industry claim.
