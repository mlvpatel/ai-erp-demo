# AI workflow lifecycle

Use this workflow before adding or expanding any AI-assisted ERP feature. The
default policy is still draft-only: AI may retrieve, classify, summarize,
explain, draft, or propose, but deterministic ERP code and authorized people
perform consequential business mutations.

## Statuses

### Proposed

A proposed AI workflow is a discovery/design idea.

- Do not add a control-plane route yet.
- Complete `docs/security/ai-workflow-review.md`.
- Identify the ERP record that remains the source of truth.
- List the exact fields that may leave the Frappe site.
- Reject the workflow if it requires customer exports, private attachments,
  secrets, payroll, bank, tax, stock valuation, or ledger lines.

### Approved for implementation

An approved workflow has a reviewed data boundary and contract plan.

- Add or update a machine-readable data-boundary manifest.
- Add a versioned OpenAPI or event contract before crossing a service boundary.
- Keep request and response models strict: unknown fields must be rejected.
- Define the `proposal_type`, `policy.decision`, `policy.allowed_action`, and
  model/prompt metadata that will be recorded.
- Add negative tests for unsupported action fields and forbidden payload data.

### Implemented

An implemented workflow has code, tests, contracts, and documentation.

- The route must return a proposal with `policy.decision = draft_only` and
  `policy.allowed_action = none` unless a future ADR explicitly changes this.
- Approval or rejection must record review only; it must not create invoices,
  post stock, change payroll, alter permissions, or submit compliance filings.
- The payload builder must send only allow-listed fields and cited source
  hashes.
- The AI Proposal record must preserve request ID, input/output hashes, model
  metadata, prompt version, sources, requester, reviewer, and review outcome.
- The workflow must appear in `config/ai-workflow-registry.json`.

## Current approved workflow

The only implemented workflow is `service_closeout_summary`:

- route: `POST /v1/proposals/service-closeout-summary`,
- proposal type: `service_closeout_summary`,
- policy: `draft_only`,
- allowed action: `none`,
- data boundary: `config/ai-data-boundary.json`,
- proof commands: `python3 scripts/check-ai-data-boundary.py`,
  `scripts/dev.sh control-plane-test`, `scripts/dev.sh contract-test`, and
  `scripts/dev.sh service-test`.

## Required change set for a new implemented workflow

A new implemented workflow must update:

1. `config/ai-workflow-registry.json`,
2. a data-boundary manifest,
3. `contracts/openapi/` or `contracts/events/`,
4. request/response models in `services/ai_control_plane/`,
5. the Frappe payload builder or requester,
6. AI Proposal storage/review documentation if review behavior changes,
7. unit, contract, and ERP workflow tests,
8. `docs/security/ai-workflow-review.md`,
9. `docs/security/threat-model.md`,
10. `docs/product/requirements-traceability.md`.

Do not add production model adapters, retrieval tools, new datastores, or
external tool calls without an ADR.
