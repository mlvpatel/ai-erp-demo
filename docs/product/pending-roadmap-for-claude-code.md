# Pending Roadmap for Claude Code

Use this file as the continuation handoff for the AI ERP Demo. It is written
for a future coding agent working in this repository.

Last known project state:

- Repository path: `/Users/mlvpatel/Downloads/ERP demo`
- Branch: `main`
- Latest known commits on main include: Production demo (#9), Retrieval
  foundation (#8), Production readiness (#7)
- ADRs through `0011-repair-memory-proposal-type.md` exist (also 0009
  scheduling explanation, 0010 exception recovery)
- Current release claim: private zero-cost local synthetic **Demo Version**
  (`config/demo-version.json`; loop `docs/product/demo-version-loop.md`; stack
  `docs/product/demo-version-stack.md`)
- Improvement plan (unique / governed / secure, agent-executable vs blocked):
  `docs/product/improvement-plan-unique-governed-secure.md`
- Current product target: governed AI-native field-service ERP for maintenance,
  installation, and repair firms with 10 to 100 technicians
- Scorecard: see `config/field-service-9-scorecard.json` — current demo average
  is below 9 and must not be treated as a shipped 9/10 product claim

Do not call the system production ready, human UAT approved, legally approved,
GDPR compliant, or full multi-industry ERP until separate evidence exists.

## Mandatory start instructions

Before making any ERP change, read these files:

1. `AGENTS.md` (root entrypoint; details in `.agents/AGENTS.md`)
2. `.agents/skills/erp-build-and-minimal-change/SKILL.md`
3. `.agents/skills/ai-governance-and-gates/SKILL.md`
4. `docs/workflows/quality-gates.md`
5. `docs/product/field-service-9-target.md`
6. `config/field-service-9-scorecard.json`
7. The files directly touched by the task

Follow these repository rules:

- Use ERPNext/Frappe as the upstream ERP platform.
- Add custom behavior only in `apps/`.
- Put cross-industry behavior in `apps/ai_erp_core/`.
- Put field-service behavior in `apps/ai_erp_service/`.
- Put model-provider calls, prompts, retrieval, redaction, and evaluation in
  `services/ai_control_plane/`.
- Version external APIs and business events in `contracts/`.
- Write an ADR in `docs/adr/` before adding a new service, datastore, external
  provider, major dependency, or irreversible architecture decision.
- Use synthetic data only.
- Never commit secrets, customer data, production backups, generated ERPNext
  source, LAFI files, RAGFlowPro files, or unrelated project artifacts.
- AI must never directly post accounting, stock, payroll, permissions,
  compliance records, or customer messages.
- AI may retrieve, classify, summarize, draft, explain, or propose.
- Deterministic ERP code and authorized humans must perform business-state
  changes.

If committing, use only:

- Author: `mlvpatel <mlvpatel@users.noreply.github.com>`
- Committer: `mlvpatel <mlvpatel@users.noreply.github.com>`
- No AI, LLM, bot, assistant, or generated-by attribution in commits.

## What is complete now

The local synthetic demo is complete enough to show privately.

Implemented and verified on `main`:

- Repository structure, license, contamination controls, and private GitHub PR
  history through production-readiness and retrieval foundation merges.
- Field-service Service Request to Service Work Order flow.
- Technician assigned-work scope.
- Manager closeout, parts issue, invoice-ready transition, and exception flow.
- Accounts-only draft Sales Invoice creation.
- Draft invoices are idempotent, draft-only, and do not update stock.
- Parts issue is idempotent and uses deterministic ERPNext Stock Entry.
- Finance/profitability fields are hidden from technicians.
- AI closeout proposal is draft-only, cited, immutable, review-only, and
  non-posting.
- Deterministic scheduling suggestions plus draft-only scheduling explanation
  proposals (ADR 0009).
- Exception recovery draft proposals (ADR 0010).
- Repair-memory draft proposals with template and OpenAI paths (ADR 0011);
  OpenAI path must redact before provider call and record audit metadata.
- Permission-scoped structured retrieval for field-service AI context
  (Retrieval foundation #8) — not a vector store.
- Margin-risk classification helpers and manager/finance margin leakage summary
  API (deterministic; not a full intelligence product).
- Evidence chain/packet APIs; evidence timeline and replay UI exist as demo
  surfaces and still need polish/tests before claiming ledger completeness.
- Distribution and light manufacturing configured demos exist as
  `configured_demo`, not implemented industry packs.
- Zero-cost deterministic `template` provider works for demo governance.
- OpenAI adapter exists with spend/redaction controls; live provider evaluation
  gate is not complete.
- Phase 1 scorecard and design-partner template are in place.
- Phase 2 field-service foundations are in place:
  - Service Asset
  - Service Priority
  - SLA Due At
  - Warranty Status
  - Inspection Required
  - Inspection Result
  - Inspection Notes
  - closeout validation for required inspection evidence

Current quality evidence (re-verify on the branch you are shipping):

- `scripts/run-quality-gates.sh` is the always-run static gate.
- Python lint (pinned ruff) is a separate CI/pre-commit path — not optional
  host-tool detection inside the always-run gate.
- Control-plane, contract, ERP service, and e2e gates via `scripts/dev.sh`
  when those areas change.

## What is pending / WIP (honest)

Still open relative to the field-service 9/10 target — do not mark these done
without fresh evidence:

- Live OpenAI evaluation gate and private safe aggregate recording (blocked on
  credentials + private aggregate storage).
- Design-partner validation, human UAT, legal/support/go-no-go gates (external).
  In-repo demo legal-readiness package exists under `docs/compliance/`
  (privacy inventory, PII notes, DPA/DPIA templates, go/no-go checklist). Those
  artifacts are not counsel sign-off, GDPR compliance, or pilot approval.
- Offline mobile drafts: intentionally not shipped (IndexedDB helper gated off).
- Any claim of production readiness, GDPR compliance, or multi-industry ERP.

Recently closed in-repo relative to the forge audit backlog (re-verify on the
branch you are shipping):

- Unified Service Work Order Desk JS (single client path; no dual `doctype_js`).
- Explain Schedule button + dispatcher rejection-reason capture.
- Replay fixtures for scheduling explanation and exception recovery.
- Manager-facing margin-risk surfacing on evidence replay/packet.
- Deeper synthetic retrieval abstention/leakage tests.
- Evidence packet ledger-narrative polish and mobile focus/a11y CSS depth.
- Scheduling rejection feedback category rollup in Suggest Technicians /
  `suggestion_feedback_summary` (no auto-rescoring).
- Van-warehouse capability profiles and per-tech parts readiness when the
  issue_parts primary bin is short; skill/territory/SLA scheduling e2e.
- Evidence Replay Desk surface for compact ledger narrative stages
  (finance_handoff role-scoped).
- Recovery refusal edges: parts-hold guidance, uncited-history drop,
  injection/contact redaction; owned-exception Desk confirm before draft.
- Scorecard/memory resync (demo average remains below 9).

The following work remains to approach an average 9/10 field-service product.
The work should be done phase by phase, with one coherent pull request per
phase or smaller pull requests per work package when risk is high.

## Phase 3: Governed AI kernel

Goal: move from demo-grade AI governance to a useful, safe, provider-backed AI
kernel with retrieval, evaluations, limits, and abstention.

Current status:

- Deterministic template provider exists.
- OpenAI adapter and provider controls exist, including closeout and repair-
  memory redaction/audit paths; live provider validation is not complete enough
  for a 9/10 product claim.
- Structured permission-scoped retrieval exists on main (not vector search).
- Repair memory, scheduling explanation, and exception recovery proposal types
  exist as draft-only cited proposals. Margin leakage is deterministic ERP-side
  classification, not provider-backed intelligence.
- Offline drafts and full evidence-ledger product polish remain incomplete.

### Phase 3A: Provider readiness and live evaluation gate

Scope:

- Keep the existing provider adapter inside `services/ai_control_plane/`.
- Do not add another cloud provider in this phase.
- Keep the model pinned until private evaluations justify a change.
- Keep tool use disabled unless a future ADR and tests approve a typed tool.
- Keep `store=false` and redact sensitive data before provider calls.
- Keep raw prompts and raw responses out of Git, CI logs, and release evidence.

#### WS1 unblock checklist (credentials required; do not invent scores)

Live OpenAI evaluation is blocked until an operator can complete this privately.
Do not put secrets in the repo, tracked `.env`, CI logs, issues, or screenshots.

1. Confirm a private deployment/task environment (not public CI).
2. Inject `OPENAI_API_KEY` from an approved secret store only.
3. Set non-secret gates from `docs/runbooks/openai-live-evaluation.md`:
   - `AI_ERP_PROVIDER=openai`
   - `OPENAI_API_KEY_SOURCE=deployment-secret-store`
   - `AI_ERP_ENABLE_PRIVATE_LIVE_EVAL=I_ACKNOWLEDGE_SYNTHETIC_ONLY`
4. Use the pinned EU base URL and model from ADR-0006.
5. Set a project-level hard budget/alert before the run.
6. Run `python -m ai_erp_control_plane.live_eval` and keep only the safe
   aggregate stdout line as evidence.
7. Store that aggregate privately; never commit raw prompts/responses.

#### WS2 design-partner readiness (no fake partner scores)

Facilitator path for a session without an OpenAI key:

- `docs/runbooks/design-partner-facilitator.md` (stack start, roles, lever-aligned
  walkthrough, do-not-claim reminders, where to record scores)
- `docs/discovery/design-partner-validation-template.md` (blank score cells;
  lever-mapped workflow rows)
- `docs/runbooks/demo-script.md` and `docs/runbooks/local-demo.md`
- Public demo script gates via `scripts/check-demo-script.py`

Do not invent partner scores. Record only real design-partner feedback when an
external owner runs the session.

Implementation tasks:

1. Review current provider configuration and tests in:
   - `services/ai_control_plane/src/`
   - `services/ai_control_plane/tests/`
   - `contracts/openapi/ai-control-plane-v1.yaml`
   - `tests/contract/test_ai_control_plane_openapi.py`
2. Add or tighten provider contract cases for:
   - request shape
   - schema rejection
   - timeout
   - provider unavailable
   - malformed output
   - rate limit
   - model mismatch
   - PII redaction
   - credential redaction
   - invented quantity refusal
   - prompt injection refusal
3. Add a private live-evaluation runbook or script path that:
   - requires explicit local or protected-environment acknowledgement
   - requires secrets to come from an approved secret source
   - uses synthetic or approved redacted inputs only
   - records safe aggregate metadata only
   - fails closed if any safety case fails
4. Keep `/healthz` as process liveness and `/readyz` as provider readiness.
5. Ensure provider failure does not activate or promote a release.

Acceptance tests:

- `scripts/run-quality-gates.sh`
- `scripts/dev.sh control-plane-test`
- `scripts/dev.sh contract-test`
- GitHub control-plane and contract checks green
- No prompts, responses, keys, or PII in logs or artifacts

Do not do:

- Do not add OpenAI calls to distribution or manufacturing demos.
- Do not add autonomous ERP posting.
- Do not store raw prompt or response bodies.
- Do not make live OpenAI validation required for the zero-cost demo.

### Phase 3B: Permission-scoped retrieval foundation

Scope:

- Add retrieval only for field-service records.
- Retrieval must be tenant-scoped and role-scoped.
- Retrieval must return citations or abstain.
- Retrieval must not bypass Frappe permissions.

Recommended design:

- Add a retrieval adapter in `services/ai_control_plane/` for request-time
  context shaping and safety validation.
- Add deterministic Frappe payload-building code in `apps/ai_erp_service/` or
  `apps/ai_erp_core/` depending on whether it is field-service-specific or
  reusable.
- Start with simple structured retrieval from ERP records, not a vector store.
- Add an ADR before introducing a vector database, embedding model, or separate
  retrieval datastore.

Implementation tasks:

1. Define allowed source records:
   - Service Work Order
   - Service Request
   - Service Location
   - Service Closure Exception
   - AI Proposal metadata
   - linked Stock Entry identifiers and safe summaries
   - linked draft Sales Invoice identifiers and safe summaries
2. Define forbidden source fields:
   - secrets
   - credentials
   - raw attachments
   - private prompts
   - raw provider responses
   - finance-only data for unauthorized roles
3. Add citation shape to contracts if current shape is insufficient.
4. Add negative tests for:
   - technician cannot retrieve unassigned work
   - technician cannot retrieve finance-only profitability data
   - requester cannot retrieve another user's AI proposals
   - cross-site data is not returned
   - missing/weak evidence causes abstention
5. Add browser or integration proof that citations match visible records.

Acceptance tests:

- Contract tests pass.
- Integration tests prove role-scoped retrieval.
- AI proposal output includes citations or safe abstention.
- No hidden source leakage.

Do not do:

- Do not add vector search until the structured retrieval path is proven.
- Do not query documents directly from the AI control plane if it bypasses
  Frappe authorization.

### Phase 3C: Proposal v2 and replay metadata

Scope:

- Upgrade AI Proposal evidence so reviewers can understand what was proposed,
  why it was allowed or refused, and what source records were used.
- Keep raw prompts/responses out of records unless a later approved retention
  design says otherwise.

Implementation tasks:

1. Review AI Proposal DocTypes in `apps/ai_erp_core/`.
2. Add safe metadata fields if missing:
   - proposal type
   - policy decision
   - safe error category
   - input context hash
   - provider response id hash
   - model name
   - token usage
   - duration
   - source record ids
   - citation hashes
   - reviewer decision
3. Add uniqueness or idempotency where needed:
   - reference doctype
   - reference name
   - proposal type
   - input context hash
4. Add tests proving concurrent proposal requests create one proposal or return
   the existing proposal.

Acceptance tests:

- One provider call under concurrent identical proposal request.
- Retry returns existing proposal.
- Rejected proposal is immutable evidence and can feed eval fixtures.

Do not do:

- Do not allow AI Proposal approval to mutate ERP transaction records.
- Do not allow AI to approve its own proposal.

## Phase 4: Verifiable evidence-to-cash ledger

Goal: make the flagship product experience: a manager can replay the entire
path from request to verified work to invoice handoff.

Current status:

- Service Work Order stores key links to parts issue and draft invoice.
- AI proposals have source evidence.
- Profitability projection exists but is basic.
- There is no complete replay UI/export or evidence packet.

### Phase 4A: Evidence chain model

Scope:

- Build a deterministic evidence chain for Service Work Order.
- Prefer a server-side method/report over a new frontend framework.

Implementation tasks:

1. Add a method or report that returns:
   - Service Request summary
   - Service Work Order identity and status
   - customer and service location
   - service asset, priority, SLA, warranty, inspection fields
   - assigned technician
   - time entries
   - part rows
   - linked Stock Entry
   - closeout notes/evidence metadata
   - closure exception history
   - AI Proposal summary and review status
   - profitability projection
   - invoice-ready transition
   - linked draft Sales Invoice
2. Return only fields visible to the current role.
3. Add permission tests for technician, manager, accounts user, and AI approver.
4. Add audit hashes or stable ids for replay evidence.

Candidate files:

- `apps/ai_erp_service/ai_erp_service/ai_erp_service/doctype/service_work_order/`
- `apps/ai_erp_service/ai_erp_service/ai_erp_service/report/`
- `apps/ai_erp_core/ai_erp_core/ai_erp_core/doctype/ai_proposal/`
- `docs/workflows/service-operations.md`
- `config/audit-evidence.json`

Acceptance tests:

- Manager sees full evidence chain.
- Technician sees only assigned-work execution evidence, not finance-only data.
- Accounts user sees invoice handoff fields required for draft invoice.
- AI approver sees proposal/citation evidence but cannot post ERP state.
- Missing evidence produces clear validation or exception, not silent omission.

### Phase 4B: Manager replay UI

Scope:

- Add a practical ERPNext/Frappe UI path for managers.
- Do not create a separate SPA unless discovery proves Frappe Desk cannot do it.

Implementation tasks:

1. Add a custom button or report link from Service Work Order to evidence replay.
2. Add a compact manager view:
   - evidence completeness
   - unresolved blockers
   - parts issued
   - invoice handoff status
   - AI proposal status
   - margin risk status
3. Add Playwright coverage for:
   - manager opens replay view
   - technician cannot see finance-only replay fields
   - accounts user can navigate to linked draft invoice
   - keyboard navigation remains usable
   - mobile viewport does not hide critical controls

Acceptance tests:

- Browser test covers the UI through visible controls.
- No API-only primary journey for the main replay path.
- Unauthorized controls are hidden or disabled and server-side blocked.

### Phase 4C: Evidence packet export

Scope:

- Produce a sanitized internal evidence packet.
- Export must not include credentials, raw prompts, raw provider responses, or
  private customer data in demo fixtures.

Implementation tasks:

1. Create a manager-only export or printable view.
2. Include:
   - work-order summary
   - audit event ids
   - source record ids
   - citation ids
   - draft invoice link
   - stock issue link
   - unresolved exceptions
   - AI policy decision
3. Add publication scan coverage if generated examples are committed.
4. Add docs that synthetic export evidence is not human UAT.

Acceptance tests:

- Manager can generate export in local demo.
- Technician cannot generate finance packet.
- Export contains no raw AI prompt/response.
- Export contains no secrets or personal data.

## Phase 5: Bounded scheduling and exception agents

Goal: add useful operational intelligence without giving AI business-state
authority.

Current status:

- Dispatcher assignment is manual.
- Cannot Close exception flow exists.
- AI closeout draft exists.
- No scheduling optimizer exists.

### Phase 5A: Deterministic scheduling optimizer

Scope:

- Start with deterministic scoring before AI explanations.
- Optimizer proposes assignments only.
- Dispatcher must approve, edit, or reject.

Recommended data:

- technician user
- skills or service categories
- territory or service area
- availability window
- workload count
- service location
- SLA due time
- service priority
- required parts readiness
- estimated duration

Implementation tasks:

1. Decide whether to use ERPNext-native fields or custom child DocTypes.
2. Add minimal data model:
   - technician skill/territory capability
   - work-order required skill/category
   - scheduling score reasons
3. Add server-side scoring method:
   - no hidden reassignment
   - deterministic tie-breaker
   - bounded candidate count
   - bounded date window
4. Add dispatcher UI:
   - ranked suggestions
   - reason summary
   - approve/edit/reject
5. Add rejection reason capture for future optimization.

Acceptance tests:

- Dispatcher sees ranked candidates.
- Technician cannot view another technician's queue through optimizer.
- Optimizer cannot assign by itself.
- Missing skill/location/availability creates exception or abstention.
- Ties are deterministic.
- Search remains bounded at smoke scale.

Do not do:

- Do not add autonomous scheduling.
- Do not add AI until deterministic scoring works.

### Phase 5B: AI scheduling explanation

Scope:

- AI may explain deterministic suggestions.
- AI may not assign technicians.

Implementation tasks:

1. Add proposal type in AI workflow registry.
2. Add contract if needed.
3. Provide source citations:
   - technician capability
   - work priority
   - SLA
   - service location
   - workload
4. Add refusal cases:
   - missing availability
   - insufficient skill evidence
   - role cannot see technician data
   - prompt injection

Acceptance tests:

- Proposal is draft-only.
- Dispatcher approval remains deterministic Frappe action.
- AI explanation cannot change assignment.

### Phase 5C: Cannot-close recovery proposal

Scope:

- AI drafts recovery steps for unresolved work.
- Manager owns action and closure.

Implementation tasks:

1. Add proposal type for exception recovery.
2. Source allowed records:
   - Cannot Close reason
   - service asset
   - inspection result
   - parts required
   - prior work-order history if retrieval exists
3. Add UI action for manager to request recovery draft.
4. Add review workflow.

Acceptance tests:

- AI draft cites exception and work-order records.
- AI cannot close work.
- Manager can reject with reason.
- Weak evidence causes abstention.

## Phase 6: Repair memory and margin intelligence

Goal: turn accumulated field evidence into reusable, cited operational insight.

Current status:

- Closeout summaries have citations.
- Structured repair memory is not implemented.
- Basic margin projection exists.
- Margin leakage categories and alerts are not implemented.

### Phase 6A: Provenance-based repair memory

Scope:

- Reuse previous fixes only when the current role can see source records.
- Start with structured query over existing records.
- Add vector retrieval only after ADR and evaluation.

Implementation tasks:

1. Add synthetic historical work-order fixtures:
   - repeated failure
   - successful fix
   - failed fix
   - missing evidence
   - unrelated customer
   - unassigned technician
2. Add retrieval method:
   - tenant/site scoped
   - role scoped
   - bounded result count
   - source ids and citation hashes
3. Add proposal type:
   - likely fix
   - missing diagnostic step
   - parts likely required
   - abstention reason
4. Add eval cases:
   - factual grounding
   - invented parts refusal
   - prompt injection
   - cross-customer leakage
   - invisible source refusal
5. Add reviewer feedback loop:
   - approve
   - reject
   - reason category
   - eval fixture candidate

Acceptance tests:

- Role-scoped retrieval blocks hidden records.
- Proposal cites visible historical work orders.
- Weak evidence returns abstention.
- No raw prompts/responses are stored.

### Phase 6B: Margin leakage guardian

Scope:

- Give managers and finance users a safe explanation of margin risk.
- Do not expose finance-only data to technicians.
- Do not auto-change billing.

Leakage categories:

- missing billable time
- repeated visit risk
- part cost above bill rate
- missing part bill rate
- warranty risk
- discount or zero-rate labor
- unresolved exception before invoice handoff
- failed inspection or follow-up result

Implementation tasks:

1. Extend profitability report or add margin risk report.
2. Add deterministic risk classifier first.
3. Add manager/finance-only fields or report columns.
4. Add AI explanation only after deterministic categories exist.
5. Add negative permission tests:
   - technician cannot see margin risk detail
   - technician cannot modify bill rates
   - unrelated customer/site data is hidden
6. Add browser tests for report visibility.

Acceptance tests:

- Manager sees risk categories and evidence.
- Accounts user sees finance handoff risk.
- Technician cannot see finance-only risk details.
- Missing cost data creates exception or unknown state, not invented margin.

### Phase 6C: Mobile field execution depth

Scope:

- Make technician workflow fast and safe on mobile.
- Keep Frappe-native UI unless discovery proves a separate app is needed.

Implementation tasks:

1. Improve Playwright mobile viewport coverage.
2. Cover:
   - assigned work list
   - execution state
   - time entry
   - parts request/use
   - inspection result
   - closeout notes
   - attachment metadata
   - validation messages
   - cannot-close path
3. Add keyboard/accessibility checks.
4. Add offline-safe draft capture only after UAT proves the need.

Acceptance tests:

- Mobile viewport works for technician journey.
- Text does not overflow critical controls.
- Validation messages point to missing fields.
- No finance/customer/assignment controls are editable by technician.

## Phase 7: Production-pilot proof

Goal: prove a secure field-service production pilot. This is not required for
the zero-cost demo, but it is required before claiming production readiness.

Current status:

- AWS/IaC and protected workflows exist as static/prepared artifacts.
- No AWS apply is approved.
- No live OpenAI pilot evaluation evidence is approved.
- No full-capacity, restore, deletion, rollback, human UAT, legal, support, or
  go/no-go evidence exists.

### Phase 7A: Deployment readiness

Prerequisites:

- AWS account approved
- OIDC or credentials approved
- domain and certificate approved
- private Terraform values approved
- recurring cost estimate reviewed
- support owner named
- legal/DPA/DPIA route decided
- explicit authorization for billable AWS and OpenAI actions

Implementation tasks:

1. Review `infra/aws/terraform/`.
2. Validate protected operations:
   - plan
   - foundation
   - activate
   - rollback
3. Ensure no broad delete policy:
   - allow reviewed ECS replacements
   - reject delete-only actions
   - reject protected resource replacements unless explicitly approved
4. Verify:
   - ECS task definitions
   - task sizing
   - autoscaling
   - Secrets Manager references
   - ALB/WAF
   - RDS TLS
   - Valkey/Redis security group
   - CloudWatch logs and alarms
   - budget alerts
5. Run Terraform format, init, validate, policy checks, and cost review.

Acceptance tests:

- Static IaC checks pass.
- Terraform plan policy rejects protected deletes.
- Secrets are never Terraform outputs.
- No AWS apply without explicit approval.

### Phase 7B: Immutable image release

Scope:

- Build, scan, sign, and publish images by digest.

Implementation tasks:

1. Build Frappe/ERPNext image from official Frappe Docker custom-image workflow.
2. Pin upstream commit and image digest.
3. Include ERPNext and local apps without vendoring upstream source.
4. Harden AI image:
   - pinned base digest
   - multi-stage build
   - non-root user
   - read-only filesystem support
   - health check
   - no test files in runtime image
5. Produce:
   - SBOM
   - vulnerability scan
   - provenance
   - signature
6. Block promotion on unresolved HIGH or CRITICAL findings.

Acceptance tests:

- Image-security checks pass.
- Deployment verifies digest, signature, provenance, SBOM, source commit, and
  scan result.

### Phase 7C: Full capacity and concurrency

Full private capacity profile:

- 250 customers
- 500 locations
- 750 items
- 1,000 service requests
- 5,000 work orders
- 10,000 time rows
- 10,000 part rows
- 1,000 AI proposals
- 2,000 Stock Entries
- 1,000 draft Sales Invoices

Measure:

- permission-scoped lists
- search
- queue age
- closeout
- invoice drafting
- AI proposals
- profitability reporting
- margin risk reporting
- evidence replay
- retrieval

Concurrency gate:

- ten parts-issue requests
- at least five authenticated manager sessions
- exactly one Stock Entry
- no double issue
- no partial issue state
- idempotent retry behavior

Acceptance tests:

- `scripts/run-full-capacity.sh` or equivalent protected command passes.
- Results are stored as private release evidence.
- Results contain synthetic data only.
- No public full-capacity claim until the exact profile passes.

### Phase 7D: Recovery and rollback

Scope:

- Prove backup, restore, deletion, service recovery, and rollback drills.

Implementation tasks:

1. Run backup drill.
2. Verify logical/file backup RPO no more than 24 hours.
3. Verify database RPO no more than 15 minutes.
4. Run restore drill in temporary recovery stack and separate Terraform state.
5. Validate after restore:
   - roles
   - tenant isolation
   - AI audit hashes
   - transaction links
   - private-file authorization
   - evidence replay
6. Run rollback drill:
   - previous ECS task definition
   - previous image digest
   - migration compatibility check
7. Delete recovery stack after validation.

Acceptance tests:

- Restore evidence proves checklist.
- Rollback evidence proves service can return to prior version.
- Incompatible migration blocks automated rollback promotion.

### Phase 7E: Human gates

These cannot be completed by code alone:

- design-partner validation
- human UAT
- legal review
- DPA/DPIA decision
- support owner
- on-call/escalation path
- accountable pilot go/no-go

Agent-completable package (already in `docs/compliance/`; keep truthful):

- `privacy-data-flow-inventory.md`
- `pii-handling-notes.md`
- `dpa-template.md` and `dpia-template.md` (templates for counsel, not signed)
- `pilot-go-no-go-checklist.md` (empty human sign-off fields)
- `eu-italy-gdpr-readiness.md` and `service-operations-pilot-evidence-template.md`

Acceptance criteria:

- Human sign-off records exist.
- `automated_complete`, `deployment_evidence_complete`, and
  `pilot_approved` remain separate states.
- No synthetic test is presented as human approval.
- Presence of compliance templates must not be scored as legal approval.

## Configured demos pending work

Distribution and light manufacturing remain `configured_demo`.

Distribution pending:

- Keep standard ERPNext-only.
- No custom distribution AI routes.
- No autonomous stock posting.
- Complete evidence through:
  - draft Sales Order
  - Pick List
  - shortage review
  - draft Delivery Note handoff
- Verify warehouse permissions.
- Verify shortage visibility.
- Verify retry safety.
- Add or update manifest, reset procedure, walkthrough, expected results, and
  integration/browser evidence.
- Promote only after design-partner validation.

Light manufacturing pending:

- Keep standard ERPNext-only.
- No custom MRP logic.
- No manufacturing AI route.
- Complete evidence through:
  - demand
  - BOM
  - production plan or work order
  - material shortage
  - draft Material Request or manual exception handoff
- Verify role permissions.
- Verify BOM calculations.
- Verify material shortage handling.
- Verify retry safety.
- Add or update manifest, reset procedure, walkthrough, expected results, and
  integration/browser evidence.
- Promote only after design-partner validation.

## Documentation pending work

Keep Demo Version discoverability current when the loop or stack pins change:

- `config/demo-version.json`
- `docs/product/demo-version-loop.md`
- `docs/product/demo-version-stack.md`
- `docs/product/improvement-plan-unique-governed-secure.md` (when build
  priority or agent-only ceiling notes change)

Update these whenever behavior changes:

- `README.md`
- `ROADMAP.md`
- `BACKLOG.md`
- `CHANGELOG.md`
- `docs/product/requirements-traceability.md`
- `docs/product/field-service-9-target.md`
- `config/field-service-9-scorecard.json`
- `docs/workflows/service-operations.md`
- `docs/workflows/ai-workflow-lifecycle.md`
- `docs/security/threat-model.md`
- `docs/runbooks/local-demo.md`
- `docs/runbooks/demo-script.md`
- relevant ADRs in `docs/adr/`

Do not update these to overclaim:

- production readiness
- legal approval
- UAT completion
- full multi-industry coverage
- real AI model quality
- broad autonomous ERP behavior

## Validation commands

Run the smallest relevant gate first, then the broader gate.

For documentation-only changes:

```sh
python3 scripts/check-doc-links.py
scripts/run-quality-gates.sh
```

For AI control-plane or contract changes:

```sh
scripts/run-quality-gates.sh
scripts/dev.sh control-plane-test
scripts/dev.sh contract-test
```

For Frappe app, permission, stock, invoice, closeout, AI Proposal, or workflow
changes:

```sh
scripts/run-quality-gates.sh
scripts/dev.sh migrate
scripts/dev.sh service-test
scripts/dev.sh e2e-test
```

For performance-sensitive changes:

```sh
scripts/run-quality-gates.sh
scripts/dev.sh performance-smoke
```

Before release or PR-ready state:

```sh
scripts/run-quality-gates.sh
scripts/check-publication-source.sh --strict
python3 scripts/check-publication-secrets.py
```

GitHub PR checks must be green before declaring a phase complete.

## Recommended implementation order

For uniqueness vs SaaS copilots and an agent-only path toward ~8.5, prefer
`docs/product/improvement-plan-unique-governed-secure.md` (Phases A–E, first
three PRs). That plan reorders work so evidence ledger and deterministic ops
intelligence land before live-provider dependency.

Classic roadmap order (still valid when a human prioritizes provider readiness
first). Skip items already landed on `main` unless the remaining gap is
polish/evals:

1. Phase 3A: provider readiness and live-evaluation gate (still open;
   blocked on credentials for live aggregates).
2. Phase 3B: deepen retrieval evals/abstention — foundation already on main.
3. Phase 3C: Proposal v2 and replay metadata polish.
4. Phase 4: evidence chain/packet/timeline polish into a finished ledger UX.
5. Phase 6B: margin leakage guardian productization (deterministic helpers exist).
6. Phase 5: scheduling optimizer polish; explanation/recovery drafts exist.
7. Phase 6A: repair-memory eval quality (proposal type exists).
8. Phase 6C: deeper mobile field execution — offline drafts remain unshipped.
9. Phase 7: production-pilot proof after external approvals.

Reasoning:

- Evidence-to-cash is the flagship differentiator and should lead agent-only
  work when credentials are absent.
- Provider/retrieval/replay hardening still makes every later AI feature safer;
  live eval waits on secrets.
- Margin leakage is immediately valuable and uses existing service data.
- Scheduling optimizer should stay deterministic before AI explanation expands.
- Production proof should wait until the product workflow is worth piloting and
  external approvals are available.

## Claude Code starter prompt

Use this prompt when continuing:

```text
Work in /Users/mlvpatel/Downloads/ERP demo on branch
codex/production-readiness.

Read AGENTS.md, .agents/skills/ai-erp-delivery/SKILL.md,
.agents/skills/erp-minimal-change/SKILL.md,
docs/workflows/quality-gates.md, docs/product/field-service-9-target.md,
config/field-service-9-scorecard.json, and
docs/product/pending-roadmap-for-claude-code.md first.

Continue the pending roadmap phase by phase. Start with Phase 3A unless I give
a different phase. Make the smallest correct change. Preserve ERPNext/Frappe
boundaries. AI must remain proposal-only and cannot post finance, stock,
payroll, permissions, compliance, or customer messages. Use synthetic data only.
Add tests and docs for every behavior change. Run the relevant gates. Commit
only as mlvpatel <mlvpatel@users.noreply.github.com> with no AI/LLM attribution.
Stop and ask if the task needs AWS/OpenAI spend, credentials, legal approval,
production deployment, customer data, or a human product decision.
```

## Completion definition for the full 9/10 target

The 9/10 target is not complete until all are true:

- Field-service evidence-to-cash ledger is complete and replayable.
- Role-scoped UI and server permissions agree.
- AI retrieval is permission-scoped and cited.
- AI proposals are evaluated, idempotent, replayable, and draft-only.
- Margin leakage and repair memory work with citations and abstention.
- Scheduling optimizer proposes only and is dispatcher-approved.
- Mobile technician workflow is usable and tested.
- Full private capacity profile passes.
- Backup, restore, rollback, and deletion drills pass.
- Live provider evaluation passes with approved synthetic/redacted inputs.
- Human UAT and design-partner validation are complete.
- Legal/support/go-no-go gates are complete.
- The scorecard reaches at least 9.0 average with evidence.
- The repository still passes all local and GitHub gates.
