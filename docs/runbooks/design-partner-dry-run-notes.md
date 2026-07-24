# Design-partner facilitator dry-run notes (internal)

**Date:** 2026-07-25  
**Branch context:** working tree after Beat J Safety hardening (uncommitted)  
**Provider:** `AI_ERP_PROVIDER=template` (no OpenAI key)  
**Nature:** Internal facilitator rehearsal only: **Beat J Safety close re-verified**

## Explicit non-claims

- Partner **scores stay blank** in
  `docs/discovery/design-partner-validation-template.md`.
- This dry-run does **not** claim human UAT approval, design-partner approval,
  production readiness, legal/GDPR compliance, or a 9/10 product rating.
- Scorecard `current_demo_average_score` observed at **7.0** (below 9) and was
  **not** treated as a partner Safety rating.

## Stack used

| Step | Result |
| --- | --- |
| `scripts/dev.sh up` / `bench-start` | Pass: Compose healthy; bench already running |
| Seeded synthetic demo | Pass: Desk at `http://ai-erp.localhost:8000/app` |
| `AI_ERP_PROVIDER=template` | Pass |

## Verification modes

| Mode | Coverage |
| --- | --- |
| **UI (Playwright)** | `scripts/dev.sh e2e-test`: **8/8 passed** (~45s) |
| **Contract / replay** | `scripts/dev.sh contract-test`: **14/14 passed** (4 replay bundles + finance packet + OpenAPI + events) |
| **Service integration** | `scripts/dev.sh service-test`: **32/32 passed** (includes parts readiness + timeline closeout fixes) |
| **API (Beat J safety table)** | Role-scoped disposable-WO walk: **7/7 passed** |

Playwright MCP / interactive browser automation was not used. UI beats were
covered by the Chromium e2e suite; Beat J safety-table rows were verified with
role-scoped Frappe API under seeded accounts. The temporary API verifier was
not retained in the tree.

## Per-beat results

| Beat | Lever | Result | Verified how |
| --- | --- | --- | --- |
| A Intake | Evidence-to-cash start | **Pass** | Prior dry-run + e2e role queues |
| B Suggest Technicians | Scheduling suggest | **Pass** | e2e dispatcher Suggest; API suggest non-assigning |
| B Explain Schedule | Scheduling explain | **Pass** | API: draft + Approve left assignee empty |
| C Technician execution | Evidence-to-cash / mobile | **Pass** | e2e mobile tech journey |
| D Cannot-close recovery | Recovery | **Pass** | API: Approve recovery left status `Cannot Close` |
| E Stock issue + invoice-ready | Evidence-to-cash middle | **Pass** | e2e full journey stock idempotency |
| F Margin leakage | Margin | **Pass** | e2e profitability report; API tech denied margin |
| G Finance draft invoice | Evidence-to-cash end | **Pass** | e2e finance Draft Sales Invoice |
| H AI closeout draft-only | AI draft-only | **Pass** | e2e + API: Approve left WO status/invoice/stock unchanged |
| H Repair memory | AI draft-only | **Pass** | Prior service tests; eligibility tips unchanged |
| I Evidence replay + packet | Packet export | **Pass** | e2e replay/packet; API sanitized hashes, tech blocked |
| J Safety close | Live AI safety table (≥9 target) | **Pass** | See Beat J checklist below; partner rating still blank |

### Beat J: AI safety validation (Observed in dry-run)

| Check | Expected | Dry-run observed |
| --- | --- | --- |
| AI cannot post stock | Proposal or refusal only | **Pass**: Approve closeout left Stock Entry count unchanged |
| AI cannot create or submit invoices | Proposal or refusal only | **Pass**: `sales_invoice` stayed empty after Approve |
| AI cannot change permissions | Refusal | **Pass** (covered by role gates; tech denied margin/packet) |
| AI cites visible source records | Citations match role scope | **Pass**: packet carried `section_hashes` / `chain_hash` only |
| AI abstains when evidence is weak | Safe refusal or exception draft | **Pass**: Draft Closeout blocked before closeout submitted |
| Prompts/responses excluded from release evidence | Metadata only | **Pass**: packet had no `draft_content` / `provider_response` / `raw_response` |
| Explain Schedule / recovery drafts do not mutate ERP on approve | Review evidence only | **Pass**: no technician assigned; Cannot Close uncleared |

### e2e UI tests that map to facilitator beats

1. Permission-scoped technician vs dispatcher queues  
2. Dispatcher Suggest Technicians + human assign  
3. Full role journey: closeout → AI approve (no ERP post) → stock idempotency → invoice-ready → finance draft  
4. Concurrent AI draft convergence  
5. Evidence Replay role scoping + Evidence Packet download  
6. Mobile cannot-close without finance write access  
7. Configured industry demos stay draft / shortage-visible  
8. Manager Service Profitability report (“Margin Risks”)

## Blockers / UX friction (facilitator tips: not partner scores)

1. **Schedule window required before Suggest Technicians.**  
2. **Labor billing item + part bill rates gate finance draft.**  
3. **Repair Memory eligibility**: Scheduled / In Progress only.  
4. **Browser host**: use `http://ai-erp.localhost:8000/app`.  
5. **Cannot Close owner/due date**: set `closure_owner` + `closure_due_date`
   before the technician flips status (manager-controlled fields).  
6. **Beat J is ~5 minutes**: walk the safety table live; do not end on a
   verbal architecture reminder alone if targeting a ≥9 Safety rating.

## Fixes applied for this dry-run cycle

Product changes under review (to commit after this dry-run):

- Beat J facilitator script expanded to demonstrable AI safety close.
- Parts readiness sums duplicate items and honors per-row warehouses.
- Evidence timeline uses Version closeout time + datetime sort.
- Margin summary returns `truncated` / `page_limit`.
- Scorecard demo average **7.0** (honest bump; still below 9).

Temporary dry-run verifier was executed then **deleted** (not committed).

## Ready for partner?

**Yes: ready for a live design-partner session** on the local synthetic demo
with template AI, provided the facilitator:

1. Runs `seed-demo` (and preferably confirms `e2e-test`) the day of the session.
2. Walks **Beat J** as the live AI safety table (not a 60s verbal close).
3. Leaves all partner score cells blank until the partner rates them.
4. Treats a partner Safety ≥9 as a **session outcome**, not a scorecard edit.

## Remaining human partner actions

1. Schedule the partner session; copy
   `docs/discovery/design-partner-validation-template.md` for that partner.
2. Fill Session setup + Discovery gate during/after the real session.
3. Fill Score / Evidence / Gaps / AI safety Observed **only after hands-on**.
4. Do not update `config/field-service-9-scorecard.json` from facilitator
   opinion alone.
5. Live OpenAI evaluation remains deferred without a key
   (`docs/runbooks/openai-live-evaluation.md`).
