# Design-partner facilitator dry-run notes (internal)

**Date:** 2026-07-25  
**Branch context:** `main` @ `968ba74` (WS2 facilitator runbook merged)  
**Provider:** `AI_ERP_PROVIDER=template` (no OpenAI key)  
**Nature:** Internal facilitator rehearsal only

## Explicit non-claims

- Partner **scores stay blank** in
  `docs/discovery/design-partner-validation-template.md`.
- This dry-run does **not** claim human UAT approval, design-partner approval,
  production readiness, legal/GDPR compliance, or a 9/10 product rating.
- Scorecard `current_demo_average_score` observed at **6.9** and was **not**
  changed.

## Stack used

| Step | Result |
| --- | --- |
| `scripts/dev.sh up` | Pass — Compose services healthy |
| `scripts/dev.sh bench-start` | Pass — already running |
| `scripts/dev.sh seed-demo` | Pass — synthetic request `SVC-REQ-.00002`, WO `SVC-WO-.00003` |
| `AI_ERP_PROVIDER=template` | Pass |
| Desk URL | `http://ai-erp.localhost:8000/app` (Host header required; bare `127.0.0.1:8000` → 404) |

## Verification modes

| Mode | Coverage |
| --- | --- |
| **UI (Playwright)** | `scripts/dev.sh e2e-test` — **8/8 passed** (~42s) |
| **API (role-scoped bench)** | Facilitator beat walk on disposable synthetic WOs — **18/18 passed** |

Playwright MCP / interactive browser automation was not used. UI beats were
covered by the existing Chromium e2e suite; remaining lever checks used
role-scoped Frappe API under the seeded accounts.

## Per-beat results

| Beat | Lever | Result | Verified how |
| --- | --- | --- | --- |
| A Intake | Evidence-to-cash start | **Pass** | API: seed request + WO; UI: role queues / forms in e2e |
| B Suggest Technicians | Scheduling suggest | **Pass** | API: ranked candidates + exclusions; UI: dispatcher Suggest dialog |
| B Explain Schedule | Scheduling explain | **Pass** | API: draft AI Proposal, assignee unchanged |
| C Technician execution | Evidence-to-cash / mobile | **Pass** | API: time + parts; privileged actions blocked; UI: mobile tech journey |
| D Cannot-close recovery | Recovery | **Pass** | API: exception + Draft Recovery Steps; UI: cannot-close path |
| E Stock issue + invoice-ready | Evidence-to-cash middle | **Pass** | API: idempotent Material Issue; UI: concurrent issue + invoice-ready |
| F Margin leakage | Margin | **Pass** | API: profitability report + tech blocked; UI: Service Profitability report |
| G Finance draft invoice | Evidence-to-cash end | **Pass** | API: draft SI, no stock update, manager blocked; UI: finance Draft Sales Invoice |
| H AI closeout draft-only | AI draft-only | **Pass** | API: approve leaves ERP status/invoice unchanged (`development-template`); UI: Draft AI Closeout + Approve |
| H Repair memory | AI draft-only | **Pass** | API: draft on In Progress WO only |
| I Evidence replay + packet | Packet export | **Pass** | API: sanitized packet keys, tech blocked; UI: replay dialog + packet download |
| J Safety close | Governance reminder | **Pass** | Confirmed; scores blank; demo average unchanged |

### e2e UI tests that map to facilitator beats

1. Permission-scoped technician vs dispatcher queues  
2. Dispatcher Suggest Technicians + human assign  
3. Full role journey: closeout → AI approve (no ERP post) → stock idempotency → invoice-ready → finance draft  
4. Concurrent AI draft convergence  
5. Evidence Replay role scoping + Evidence Packet download  
6. Mobile cannot-close without finance write access  
7. Configured industry demos stay draft / shortage-visible  
8. Manager Service Profitability report (“Margin Risks”)

## Blockers / UX friction (facilitator tips — not partner scores)

1. **Schedule window required before Suggest Technicians.** Missing
   `scheduled_start` / `scheduled_end` throws instead of guessing. Set the
   window on the Draft WO before the button.
2. **Labor billing item + part bill rates gate finance draft.** Ad-hoc WOs
   without `service_billing_item` / `hourly_rate`, or tech-declared parts with
   empty bill rates, block **Draft Sales Invoice**. Seeded demo / e2e full
   workflow WOs already include these. Facilitator should confirm rates on
   manager review (Beat E) before Beat G — this also surfaces the
   `missing_part_bill_rate` margin-risk category intentionally.
3. **Repair Memory eligibility.** Available for Scheduled / In Progress only,
   not Closeout Submitted. Use a live visit WO or reopen to In Progress for
   that demo beat.
4. **Browser host.** Use `http://ai-erp.localhost:8000/app`. Hitting the site
   without the site Host name returns 404.
5. **Local env pin warnings.** `check-local-env` warns about tag-based images /
   missing full commit pins. Fine for private dry-run; update from
   `.env.example` before publishing release evidence.

No product code blockers required a fix for partner-session readiness on the
seeded path.

## Fixes applied

- **None in application code.** Dry-run script mismatches (suggest payload
  shape, `time_entries` vs `time_logs`, status transitions, billing fields)
  were corrected in the temporary verifier only; not retained as a product
  change.
- **Runbook tip** added in `design-partner-facilitator.md` for schedule window,
  billing gates, and repair-memory eligibility.

## Ready for partner?

**Yes — ready for a live design-partner session** on the local synthetic demo
with template AI, provided the facilitator:

1. Runs `seed-demo` (and preferably confirms `e2e-test` or a quick Desk smoke)
   the day of the session.
2. Uses seeded / e2e-prepared work orders for the cash path, or manually sets
   labor item + part bill rates.
3. Leaves all partner score cells blank until the partner rates them.

## Remaining human partner actions

1. Schedule the partner session; copy
   `docs/discovery/design-partner-validation-template.md` for that partner.
2. Fill Session setup + Discovery gate during/after the real session.
3. Fill Score / Evidence / Gaps **only after hands-on**; leave blanks if
   deferred.
4. Do not update `config/field-service-9-scorecard.json` from facilitator
   opinion alone.
5. Live OpenAI evaluation remains deferred without a key
   (`docs/runbooks/openai-live-evaluation.md`).
