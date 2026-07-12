# Security documentation

Security is a product requirement for AI ERP Demo, not a deployment afterthought.
Use these documents when designing ERP workflows, AI proposals, integrations,
industry packs, and GitHub contributions.

- `threat-model.md`: MVP trust boundaries, high-priority abuse cases, and
  required controls.
- `data-classification.md`: what data may be stored, committed, sent to the AI
  control plane, or used in synthetic fixtures.
- `ai-workflow-review.md`: required checklist before adding or expanding an
  AI-assisted ERP workflow.

The AI workflow lifecycle is documented in
`docs/workflows/ai-workflow-lifecycle.md`. Approved workflows are registered in
`config/ai-workflow-registry.json` and checked by
`scripts/check-ai-workflow-registry.py`.

The reusable publication scan is defined in
`config/publication-secret-scan.json` and enforced by
`scripts/check-publication-secrets.py`.

The public `SECURITY.md` explains how to report vulnerabilities. These design
documents explain how the repo should avoid creating them.
