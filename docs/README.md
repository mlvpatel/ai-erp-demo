# Documentation

Documentation is part of the product. Use the folders below instead of creating
unstructured notes at the repository root.

- `adr/`: one short decision per material architectural choice.
- `compliance/`: demo legal-readiness package (inventory, PII notes, DPA/DPIA
  templates, GDPR gate, pilot evidence, go/no-go checklist). Templates and
  gates are not legal approval or GDPR compliance.
- `discovery/`: evidence from research, interviews, and technical spikes.
- `product/`: target users, scope, KPIs, and roadmap.
- `architecture/`: context, container, component, and data-boundary diagrams.
- `security/`: threat models, data classification, and controls.
- `runbooks/`: operations and recovery procedures.
- `workflows/`: repeatable feature, bug-fix, review, and release checklists.

Start with:

- `product/demo-version-loop.md` for the Demo Version field-service path graph
  (AI proposes vs ERP/human commit).
- `product/demo-version-stack.md` for pin-accurate stack and AI integration
  facts (`config/demo-version.json`).
- `architecture/tech-stack-2026-07.md` for the July 2026 stack decision.
- `architecture/system-context-and-repository-map.md` for the contributor-facing
  product context and folder responsibility map.
- `architecture/system-boundaries.md` for the ERP, custom app, and AI approval
  boundaries.
- [`architecture/mvp-containers.md`](architecture/mvp-containers.md) for the
  compact MVP deployment and container view.
- `architecture/domain-data-model.md` for the custom DocType and ERPNext reuse
  map.
- `discovery/open-source-erp-scan-2026-07.md` for the GitHub ERP scan.
- `discovery/discovery-design-plan.md` for the discovery-to-design workflow.
- `discovery/service-operations-interview-guide.md` before validating the first
  vertical with a design partner.
- `product/public-positioning.md` and root `ROADMAP.md` before preparing the
  public GitHub repository page.
- `product/requirements-traceability.md` before claiming the original goal is
  complete.
- `runbooks/license-decision.md` before adding a root `LICENSE` or accepting
  external public contributions.
- `runbooks/backup-restore.md` before any real client data, deployment backup,
  or restore drill.
- `runbooks/incident-response.md` before handling suspected data exposure,
  approval bypass, tenant-boundary, or transaction-integrity incidents.
- `runbooks/demo-script.md` before recording README screenshots, GIFs, or a
  public walkthrough.
- [`runbooks/production-demo.md`](runbooks/production-demo.md) to run the
  production images locally as a production-style synthetic demo.
- `compliance/README.md` before discussing legal, GDPR, DPA/DPIA, support
  ownership, or pilot go/no-go. Start with the privacy inventory and templates;
  do not claim compliance from those files alone.
- `security/threat-model.md` and `security/data-classification.md` before
  adding AI workflows, integrations, fixtures, or industry packs.
- `security/ai-workflow-review.md` before adding or expanding an AI-assisted
  ERP workflow.
- `workflows/quality-gates.md` before opening a pull request or release tag.
- `workflows/migration-safety.md` before changing DocTypes, fixtures, Frappe
  patches, or migration/runbook commands.
- `workflows/integration-safety.md` before adding connector code, event
  producers, webhooks, or external adapter dependencies.
- `workflows/operations-readiness.md` before a broad demo, release, restore
  drill, or production-use discussion.
- `workflows/observability-readiness.md` before adding monitoring, alerts,
  dashboards, traces, or log-retention guidance.
- `workflows/performance-readiness.md` before changing list/search/report
  behavior, load-sensitive workflows, or inventory-heavy industry packs.
- `workflows/issue-triage.md` before turning backlog items or public GitHub
  issues into implementation work.
- `workflows/dependency-updates.md` before merging dependency, image, or
  upstream ERP pin changes.
- `workflows/upstream-upgrade-readiness.md` before changing Frappe/ERPNext
  commits, runtime image digests, Python, or Frappe Bench assumptions.
