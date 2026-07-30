# Improvement plan: unique, current, governed, secured

Plan for raising the field-service Demo Version without copying SaaS
copilots. Current demo average: **7.5 / 10**
(`config/field-service-9-scorecard.json`). Agent-only ceiling toward **~8.5**
is reachable without keys, partners, counsel, or AWS. Full **9.1** still
needs live eval, design-partner scores, and human pilot gates.

Related: [`field-service-9-target.md`](field-service-9-target.md),
[`pending-roadmap-for-claude-code.md`](pending-roadmap-for-claude-code.md),
[`demo-version-loop.md`](demo-version-loop.md),
[`demo-version-stack.md`](demo-version-stack.md),
[`public-positioning.md`](public-positioning.md).

## Positioning: what makes this repo unique

Evidence-backed claims only. These are structural, not marketing adjectives.

1. **Proposal-only AI with a hard non-post policy in code and contracts.**
   Control-plane policy is constant `draft_only` / `allowed_action: none`
   (`services/ai_control_plane/`, `contracts/openapi/ai-control-plane-v1.yaml`).
   Human approve/reject on `AI Proposal` (`apps/ai_erp_core/`) does not create
   Stock Entry or Sales Invoice. Competitors (SAP Joule, Dynamics Copilot,
   Odoo AI, NetSuite agents) sell assistant breadth that often blurs into
   write-capable actions; this repo makes non-posting the product.

2. **Evidence-to-cash ledger as the flagship, not chat.** The Demo Version
   loop is request → schedule → execute → evidence → margin → draft proposals
   → human review → invoice-ready → idempotent stock/invoice → role-scoped
   replay (`docs/product/demo-version-loop.md`,
   `apps/ai_erp_service/.../evidence.py`). Generic copilots optimize prompt UX;
   this stack optimizes a replayable finance handoff.

3. **Separate AI control plane with versioned contracts and redaction before
   provider calls.** Provider calls, prompts, retrieval shaping, and safety
   live in `services/ai_control_plane/` (`render.py`, `safety.py`). ERP
   mutations stay in Frappe apps. OpenAPI + event contracts sit in
   `contracts/`. That split is uncommon in ERP AI demos that embed LLM calls
   inside Desk scripts.

4. **Machine-checked governance, not policy PDFs alone.** Static suite
   `scripts/run-quality-gates.sh` plus
   `check-ai-workflow-registry.py`, `check-ai-data-boundary.py`,
   `check-authorization-matrix.py`, `check-tenant-isolation.py`,
   `check-publication-secrets.py`, contract/replay harnesses, and
   `config/ai-workflow-registry.json` registration for every proposal type.
   Skills under `.agents/skills/` bind the same rules to coding agents.

5. **Synthetic Demo Version packaging with explicit claim boundaries.**
   `config/demo-version.json` pins `synthetic_only`, `proposal_only`,
   `template` provider, and forbidden claims (production ready, GDPR
   compliant, human UAT, shipped 9/10). Compliance templates under
   `docs/compliance/` are worksheets, not counsel sign-off.

## Principles (non-negotiable)

### Governance

- AI proposes; deterministic ERP code and authorized humans post.
- Every proposal type is registered, typed, cited or abstaining, idempotent
  on context hash, and immutable after create.
- Custom behavior only in `apps/ai_erp_core/` and `apps/ai_erp_service/`;
  never patch upstream Frappe/ERPNext.
- New service, datastore, or provider requires an ADR in `docs/adr/` first.
- External HTTP and events stay versioned under `contracts/`.
- Quality gates scale with blast radius: always
  `scripts/run-quality-gates.sh`; add `control-plane-test`, `contract-test`,
  `service-test`, `e2e-test` when those layers change.

### Security

- Redact PII and credentials in the control plane before any hosted provider
  call (`render.py`; verified by `check-ai-data-boundary.py`).
- No secrets, raw prompts, raw provider bodies, or real customer data in Git,
  CI logs, or release evidence (`check-publication-secrets.py`).
- Role matrix: technicians never see finance/margin fields; managers own
  closeout/exceptions; accounts own draft invoice; AI Approver cannot post
  ERP state (`config/authorization-matrix.json`).
- Tenant/site isolation preserved (`check-tenant-isolation.py`).
- Parts issue and draft invoice remain idempotent Frappe methods.
- Compliance docs inventory risk; they do not claim GDPR compliance.

## Implementation plan

Phases below reorder the pending roadmap for uniqueness and agent
executability. Phase numbers here are plan phases, not a rewrite of Phase 3–7
labels in `pending-roadmap-for-claude-code.md` (cross-refs noted).

### Phase A — Deepen the differentiator (evidence ledger + proposal replay)

**Goal.** Make evidence-to-cash and safe agent replay the sharpest demo story
vs any generic copilot.

| Lens | Contribution |
| --- | --- |
| Unique | Flagship ledger UX depth; competitors cannot show this without rebuilding ERP + audit |
| Latest | Structured retrieval + typed proposals (no premature vector DB) |
| Governance | Proposal metadata completeness; registry + contract alignment |
| Security | Role-scoped replay/packet; no raw prompt storage |

**Work items (agent-executable):**

1. Finish manager Evidence Replay / packet polish:
   `apps/ai_erp_service/.../evidence.py`, Desk JS, compact ledger stages,
   finance_handoff only for permitted roles.
2. Add negative permission + e2e coverage for technician vs manager vs
   accounts packet views (`tests/e2e/service-operations.spec.ts`).
3. Proposal v2 safe metadata gaps (roadmap Phase 3C): policy category,
   citation hashes, token/duration where already returned, concurrent
   idempotency proof on `input_context_hash`.
4. Expand replay fixtures under `tests/fixtures/replay-bundles/` so every
   registered type in `config/ai-workflow-registry.json` has a cited bundle
   with `@today` relative dates.

**Success evidence:** `service-test`, `e2e-test`, `contract-test`,
`test_replay_harness.py`, quality gates green; scorecard notes updated with
paths, not invented partner scores.

**Scorecard levers:** verifiable-evidence-to-cash-ledger (8.2),
safe-agent-replay (8.0).

**Blocked-on-user:** partner packet review for ≥9.0 on those levers.

### Phase B — Deterministic ops intelligence before more LLM surface

**Goal.** Productize margin leakage and scheduling as ERP-owned intelligence
with optional AI explanation only.

| Lens | Contribution |
| --- | --- |
| Unique | Margin guardian + bounded optimizer with human commit; not “ask the bot who to send” |
| Latest | Deterministic classifiers + feedback rollups; AI explains, does not assign |
| Governance | No auto-rescoring / auto-assign; registry stays draft_only for explanations |
| Security | Finance fields stay manager/accounts-only |

**Work items (agent-executable):**

1. Margin leakage guardian productization
   (`apps/ai_erp_service/.../margin_risk.py`, profitability report, Desk
   summary): clearer category evidence links into the ledger; keep
   classification deterministic (no provider).
2. Scheduling polish (`scheduling.py`, capability DocTypes): parts-readiness
   edge cases, rejection-category rollup visibility, deterministic
   tie-breaker tests; no autonomous assignment.
3. Keep Explain Schedule / recovery as draft-only proposals; add refusal
   cases only when missing evidence or role scope fails.

**Success evidence:** authorization-matrix check, service tests for
technician denial of margin detail, e2e for manager-only margin button,
scheduling feedback summary tests.

**Scorecard levers:** margin-leakage-guardian (7.8),
bounded-scheduling-optimizer (7.5), cannot-close-recovery-coach (8.0).

**Blocked-on-user:** partner UX review for ≥9 targets.

### Phase C — Governed AI kernel without claiming live-model quality

**Goal.** Harden template-path evals, retrieval abstention, and provider
contract failures so hosted eval is a drop-in later (roadmap Phase 3A/3B/6A).

| Lens | Contribution |
| --- | --- |
| Unique | Permission-scoped structured retrieval + abstention; not RAG-over-everything |
| Latest | OpenAPI 3.1 contracts, pinned OpenAI adapter with `store=false`, spend/redaction; no second provider yet |
| Governance | Registry, ADR-0006 pins, live eval remains opt-in and synthetic-only |
| Security | Redaction, injection refusal, no raw bodies in fixtures |

**Work items (agent-executable):**

1. Tighten control-plane contract tests: schema rejection, timeout,
   unavailable, malformed output, rate limit, model mismatch, PII/credential
   redaction, invented-quantity refusal, prompt-injection refusal
   (`services/ai_control_plane/tests/`,
   `tests/contract/test_ai_control_plane_openapi.py`).
2. Expand synthetic repair-memory history corpus and retrieval edge tests
   (`repair_memory.py`, `retrieval.py`, `test_retrieval_edges.py`):
   unassigned technician, unrelated customer, weak evidence abstention,
   contact redaction.
3. Keep `/healthz` liveness vs `/readyz` provider readiness; template provider
   remains Demo Version default.

**Work items (blocked-on-user):**

- Inject `OPENAI_API_KEY` from secret store; run
  `docs/runbooks/openai-live-evaluation.md`; store safe aggregate only.
- Do not invent live eval scores.

**Success evidence:** `control-plane-test`, `contract-test`, quality gates;
Demo Version still `requires_live_openai: false`.

**Scorecard levers:** provenance-based-repair-memory (6.5),
safe-agent-replay (8.0). Live provider does not move demo average until
private aggregates exist.

### Phase D — Mobile field execution depth (online only)

**Goal.** Raise the lowest scorecard lever without shipping offline drafts.

| Lens | Contribution |
| --- | --- |
| Unique | Technician path that cannot leak finance/assignment controls |
| Latest | Frappe Desk mobile CSS + Playwright viewport proof (not a separate SPA) |
| Governance | Same permission matrix on mobile |
| Security | Assigned-work scope; forbidden fields hidden and server-blocked |

**Work items (agent-executable):**

1. Extend `public/css/mobile_field.css` and Playwright coverage at
   390×844: assigned list, time, parts, inspection, closeout, cannot-close,
   validation messages, 44px targets, accessible names.
2. Keep IndexedDB offline drafts gated off until field UAT asks for them.

**Success evidence:** e2e mobile specs green; authorization negatives still
pass.

**Scorecard levers:** mobile-field-execution (6.1). Offline remains deferred.

### Phase E — Claim hygiene and release truthfulness

**Goal.** Raise governed-demo-to-pilot without pretending pilot gates passed.

| Lens | Contribution |
| --- | --- |
| Unique | Honest Demo Version vs pilot packaging |
| Latest | Pin-accurate stack docs (`demo-version-stack.md`,
  `tech-stack-2026-07.md`); upgrade only via upstream-upgrade-readiness |
| Governance | Separate `demo ready` / `automated_complete` /
  `deployment_evidence_complete` / `pilot_approved` |
| Security | Publication scans; compliance templates labeled as non-approval |

**Work items (agent-executable):**

1. Keep `config/demo-version.json`, scorecard, ROADMAP, BACKLOG, and this
   plan aligned when levers move.
2. Maintain `docs/compliance/` accuracy; never score templates as legal
   approval.
3. Static IaC / image-security checks only; no AWS apply.

**Blocked-on-user:** counsel DPA/DPIA, support owner, UAT, go/no-go, AWS
account and budget.

**Scorecard levers:** governed-demo-to-pilot-release (7.3).

### Phase F — External pilot proof (out of agent-only path)

Maps to roadmap Phase 7. Not required for ~8.5 Demo Version ceiling.

Requires: AWS/OIDC, domain/certs, live OpenAI budget, capacity/restore/
rollback drills, design-partner + UAT, counsel, named support.

## 90-day Demo Version track (agent-only toward ~8.5)

Assume one coherent PR stream on main, template provider only, no partner
scores invented. Order maximizes uniqueness and score delta.

| Window | Focus | Expected lever moves (illustrative, evidence-gated) |
| --- | --- | --- |
| Days 1–21 | Phase A ledger + replay metadata + fixtures | ledger 8.2→~8.8; replay 8.0→~8.6 |
| Days 22–42 | Phase B margin + scheduling + recovery polish | margin 7.8→~8.5; scheduling 7.5→~8.3; recovery 8.0→~8.5 |
| Days 43–63 | Phase C synthetic repair-memory + provider contract edges | repair memory 6.5→~7.6; contract refusal coverage |
| Days 64–84 | Phase D mobile online depth | mobile 6.1→~7.8 |
| Days 85–90 | Phase E scorecard/docs/Demo Version resync | governed release 7.3→~7.8; average toward **~8.5** if evidence supports each bump |

Rough check if those land: ~8.8 + 8.5 + 8.5 + 7.6 + 8.6 + 8.3 + 7.8 + 7.8
÷ 8 ≈ **8.5**. Do not write those numbers into the scorecard until tests and
docs back them. Anything above ~8.5 needs live eval and partner ratings.

**Explicitly out of the 90-day agent path:** OpenAI live aggregates, AWS
apply, counsel sign-off, human UAT, offline IndexedDB, distribution/
manufacturing pack promotion, second LLM provider, vector database.

## Competitive “do not copy” list

Do not chase these as product goals for this repository:

1. **Chat-first ERP copilot** that answers anything in natural language
   across modules (Joule / Dynamics Copilot style breadth).
2. **Autonomous agents that post** invoices, stock, payroll, or customer
   messages without a separate deterministic ERP path.
3. **Tool-calling freestyle** against live DocTypes without typed registry,
   contracts, and `allowed_action: none`.
4. **Unscoped RAG / vector memory** over customer history before structured
   permission-scoped retrieval is proven (ADR required first).
5. **Multi-provider “AI marketplace”** before one pinned hosted path has
   private eval evidence.
6. **Greenfield SPA ERP** replacing Frappe Desk for the core loop.
7. **Compliance theater**: claiming GDPR / production / UAT from templates
   or synthetic gates alone.
8. **Industry sprawl**: promoting distribution/manufacturing beyond
   `configured_demo` before a partner validates field-service.

## Recommended first 3 PRs

1. **`Evidence ledger packet polish and role-scoped e2e`**
   Why: raises the flagship differentiator (Phase A); pure
   `apps/ai_erp_service` + e2e; no credentials; directly unique vs copilots.

2. **`Margin leakage guardian Desk depth (deterministic only)`**
   Why: second-highest ops value with zero LLM risk (Phase B); permission
   negatives make the security story visible in demo.

3. **`Repair-memory synthetic corpus and retrieval abstention edges`**
   Why: lifts the weakest AI lever without live OpenAI (Phase C); strengthens
   provenance claim that SaaS agents rarely prove in code.

After those three, prefer mobile e2e depth, then scheduling feedback UX, then
provider contract failure matrix—still agent-executable.

## How to execute each PR

1. Read `AGENTS.md`, governance/security/minimal-change skills, quality-gates
   doc, this plan, and files in the PR’s blast radius.
2. Smallest correct change; ADR if new provider/datastore/service.
3. Run proportional gates; always `scripts/run-quality-gates.sh`.
4. Update scorecard `optimization_step` / scores only with evidence.
5. Keep Demo Version claim boundary intact.
6. Commit as `mlvpatel <mlvpatel@users.noreply.github.com>` with no AI
   attribution trailers.
