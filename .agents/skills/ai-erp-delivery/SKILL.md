---
name: ai-erp-delivery
description: Plan, build, modify, or review features for the AI ERP Demo. Use when work touches a Frappe custom app, an industry pack, an AI-assisted workflow, an external ERP integration, business-event/API contracts, or ERP delivery documentation.
---

# AI ERP Delivery

Build the ERP as a modular Frappe/ERPNext product with a separately governed AI
layer. Make changes safe, explainable, testable, and suitable for reuse across
industries.

## Workflow

1. Read the repository `AGENTS.md` and the nearest relevant documentation in
   `docs/` before proposing or changing anything.
2. Classify the work as one of: horizontal core, industry pack, integration,
   AI control plane, contract, infrastructure, or documentation.
3. Keep scope in the correct boundary:
   - Put cross-industry behavior in `apps/ai_erp_core/`.
   - Put sector-specific behavior in its industry app.
   - Put provider calls, retrieval, prompting, evaluation, and AI audit records
     in `services/ai_control_plane/`.
   - Put public schemas in `contracts/` before or with the implementation.
4. Record a short ADR before introducing a datastore, service, external
   provider, or irreversible architectural dependency.
5. Implement the smallest coherent change, then add the matching tests and
   documentation.
6. Validate behavior, tenant boundaries, permissions, and failure handling
   before handoff.

## AI and transaction boundary

- Keep money, tax, inventory, payroll, permissions, and compliance state under
  deterministic ERP validation and authorization.
- Allow AI to retrieve, classify, summarize, draft, explain, or propose actions.
- Require an authorized person or deterministic workflow to approve any action
  that changes business state.
- Return citations or source references with retrieval-based answers whenever
  evidence is available.
- Record model, prompt/version, tool calls, supplied context identifiers,
  output, approval, and outcome for AI actions that affect a business process.

## Design rules

- Treat ERPNext/Frappe as upstream; extend it through custom apps instead of
  editing its source.
- Prefer Frappe's built-in permissions, workflows, background jobs, and
  real-time capabilities before adding a new frontend or distributed service.
- Design integrations as replaceable adapters with idempotent writes and an
  observable failure path.
- Use synthetic fixtures only. Never place client data, credentials, or
  production exports in the repository.
- Separate a demonstrated requirement from a future hypothesis; place the
  latter in discovery or the roadmap, not in the first implementation.

## Verification

- Run focused unit tests for business rules and contract tests for external
  boundaries.
- Exercise one end-to-end workflow when a change crosses user roles, modules,
  or services.
- Check authorization and tenant isolation explicitly; successful behavior for
  an administrator is not proof of correct behavior for other roles.
- Load-test realistic record volumes before accepting changes that alter list,
  search, reporting, or inventory behavior.
- Read `references/quality-gates.md` for discovery, release, and AI-readiness
  checks when planning a significant feature.
