# Field Service Scorecard Memory

## Benchmark Status
- **Current Demo Average Score**: 8.1 / 10
- **Target Average Score**: 9.1 / 10
- Do not treat the demo average as a shipped 9/10 product claim. Live OpenAI
  eval, design-partner / human UAT, and production/legal/GDPR evidence remain
  deferred or blocked.
- Demo Version label: `2026.07.30-demo` (`config/demo-version.json`). Loop and
  stack docs improve discoverability only; they do not raise the average.
- Agent-executable uniqueness / governance / security build order:
  `docs/product/improvement-plan-unique-governed-secure.md` (~8.5 ceiling
  without keys, partners, counsel, or AWS).
- Residual Phase A proposal metadata moved verifiable-evidence-to-cash-ledger
  8.4 → 8.6 and safe-agent-replay 8.0 → 8.3 (policy_category, citation hashes,
  token/duration in packet/timeline, concurrent context-hash reuse proof,
  invoice-handoff evidence packet, harness depth). Partner packet review still
  required for ≥9.0.
- Phase B margin Desk depth moved margin-leakage-guardian 7.8 → 8.2
  (category evidence in ledger, Desk status/date filters, Accounts report
  access, truncation honesty). Partner UX review still required for ≥9.0.
- Phase B scheduling polish moved bounded-scheduling-optimizer 7.5 → 8.5
  (van-warehouse capability, per-tech parts readiness aligned with
  issue_parts primary bins, skill/territory/SLA e2e, feedback rollup without
  auto-rescore, deterministic tie-breaker tests). Partner UX review still
  required for ≥9.0.
- Phase B recovery Desk polish moved cannot-close-recovery-coach 8.0 → 8.2
  (owned-exception confirm before draft). Partner UX review still required
  for ≥9.0.
- Phase C repair-memory corpus moved provenance-based-repair-memory 6.5 → 7.6
  (synthetic history corpus, weak-evidence abstention, unassigned /
  unrelated-customer retrieval edges, contact/injection sanitization, browser
  citation match). Live provider aggregate eval remains blocked on credentials.
- Phase D online mobile depth moved mobile-field-execution 6.1 → 7.8
  (390×844 list/time/parts/inspection/attachment/closeout/cannot-close,
  validation copy, forbidden-field matrix, IndexedDB still gated off). Field
  UAT and offline drafts remain open before ≥9.0.

## Beat J: Safety close (partner ≥9 target)
- Facilitator Beat J is now a live AI safety table walk (approve does not post,
  role-scoped packet, abstention, architecture + claim hygiene), not a 60s
  verbal reminder.
- Partner Safety ≥9 still requires a real session filling
  `docs/discovery/design-partner-validation-template.md`. Do not invent scores.

## Feature Breakdown & Gap Status

1. **Verifiable Evidence-to-Cash Ledger** (Current: 8.6 / Target: 10.0)
   - *Status*: Partly Implemented. Desk Evidence Replay shows compact ledger
     narrative stages (incomplete headline when gaps remain); finance_handoff
     is role-scoped. Timeline includes exceptions, proposal context-hash stubs,
     policy_category, and token/duration when present. Managers and accounts
     can export the sanitized packet with idempotency rows, citation hashes,
     and policy categories; technicians cannot. Concurrent context-hash reuse
     is covered in service tests. Partner packet review remains open.

2. **Cannot-Close Recovery Coach** (Current: 8.2 / Target: 9.0)
   - *Status*: Partly Implemented. Overdue escalation, cited recovery drafts,
     parts-hold guidance, uncited-history drop, injection/contact redaction,
     and owned-exception Desk confirm before draft creation. Partner UX review
     remains open.

3. **Margin Leakage Guardian** (Current: 8.2 / Target: 9.0)
   - *Status*: Partly Implemented. Managers and finance open a Desk summary
     with category counts, evidence snippets, status/date filters, capped
     high-risk queue, and truncation notices. Evidence chain/packet carry
     `margin_risk_details` (discount/zero-rate hours, neighbors, unknown cost
     items). Profitability report allows Accounts roles and warns on page
     truncation. Partner-reviewed analytics and UAT remain open.

4. **Provenance-Based Repair Memory** (Current: 7.6 / Target: 9.0)
   - *Status*: Partly Implemented. Template path uses an 8-entry synthetic
     history corpus; cite/abstain/redact/injection edges and weak-evidence
     abstention are covered in control-plane and service tests; browser
     citation match covers seeded Desk drafts. Live provider aggregate eval is
     still blocked on credentials.

5. **Safe Agent Replay** (Current: 8.3 / Target: 9.0)
   - *Status*: Partly Implemented. Four draft-only replay fixtures cite every
     history entry and use `@today` relative dates. Finance and invoice handoff
     evidence packets deepen harness coverage; approve review events stay
     draft_only with no mutation fields. Live provider replay aggregates remain
     deferred.

6. **Bounded Scheduling Optimizer** (Current: 8.5 / Target: 9.0)
   - *Status*: Partly Implemented. Capability profiles include optional
     `van_warehouse`. Parts readiness sums duplicate items, honors per-row
     `source_warehouse` (issue_parts primary), and can mark a technician
     ready from van stock when the primary bin is short. Skill/territory/SLA
     e2e, feedback rollup without auto-assign or auto-rescore, and
     workload-then-id tie-breakers are covered. Partner UX review remains open.

7. **Mobile Field Execution** (Current: 7.8 / Target: 9.0)
   - *Status*: Partly Implemented. Desk CSS covers sticky actions, attach
     controls, list rows, and grid cards at phone width. Playwright at
     390 by 844 walks assigned list, time, parts, inspection, attachment,
     closeout, cannot-close, validation copy, and a forbidden-field matrix.
     IndexedDB offline drafts remain intentionally gated off
     (`mobile_helpers.js` not in `app_include_js`).

8. **Governed Demo-to-Pilot Release** (Current: 7.3 / Target: 9.0)
   - *Status*: Partly Implemented. Demo Version packaging
     (`config/demo-version.json`, loop + stack docs) and demo gates pass. Demo
     legal-readiness package exists under `docs/compliance/`. External
     pilot/legal/UAT sign-off remains pending; artifacts are not compliance.
