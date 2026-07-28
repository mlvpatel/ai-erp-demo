# Field Service Scorecard Memory

## Benchmark Status
- **Current Demo Average Score**: 7.3 / 10
- **Target Average Score**: 9.1 / 10
- Do not treat the demo average as a shipped 9/10 product claim. Live OpenAI
  eval, design-partner / human UAT, and production/legal/GDPR evidence remain
  deferred or blocked.

## Beat J: Safety close (partner ≥9 target)
- Facilitator Beat J is now a live AI safety table walk (approve does not post,
  role-scoped packet, abstention, architecture + claim hygiene), not a 60s
  verbal reminder.
- Partner Safety ≥9 still requires a real session filling
  `docs/discovery/design-partner-validation-template.md`. Do not invent scores.

## Feature Breakdown & Gap Status

1. **Verifiable Evidence-to-Cash Ledger** (Current: 8.0 / Target: 10.0)
   - *Status*: Partly Implemented. Timeline replay uses Version-based closeout
     timestamps (filtered by Closeout Submitted marker, not an unfiltered
     first-50 page) and datetime sort keys (not `modified` / string sort).

2. **Cannot-Close Recovery Coach** (Current: 7.8 / Target: 9.0)
   - *Status*: Partly Implemented. Overdue escalation, cited recovery drafts,
     and exception-recovery replay fixtures exist. Broader refusal corpora and
     partner UX review remain open.

3. **Margin Leakage Guardian** (Current: 7.8 / Target: 9.0)
   - *Status*: Partly Implemented. Managers and finance can open a Desk
     summary dialog (category counts, capped high-risk queue, truncation
     notice). Scan truncation uses limit+1 detection; high-risk queue cap is
     flagged separately. Partner-reviewed analytics and UAT remain open.

4. **Provenance-Based Repair Memory** (Current: 6.5 / Target: 9.0)
   - *Status*: Partly Implemented. Template renderers keep only citation-backed
     history, redact contact/credential-shaped free text, and neutralize
     instruction-like spans. Live provider aggregate eval is still blocked on
     credentials.

5. **Safe Agent Replay** (Current: 8.0 / Target: 9.0)
   - *Status*: Partly Implemented. Four draft-only replay fixtures cite every
     history entry and use `@today` relative dates. Live provider replay
     aggregates remain deferred.

6. **Bounded Scheduling Optimizer** (Current: 7.3 / Target: 9.0)
   - *Status*: Partly Implemented. Parts readiness sums duplicate items and
     honors per-row `source_warehouse` (aligned with `issue_parts`).

7. **Mobile Field Execution** (Current: 6.1 / Target: 9.0)
   - *Status*: Partly Implemented. Online mobile CSS enforces 44px targets and
     readable validation copy; browser tests assert accessible names at
     390 by 844. IndexedDB offline drafts remain intentionally gated off.

8. **Governed Demo-to-Pilot Release** (Current: 7.0 / Target: 9.0)
   - *Status*: Partly Implemented. Demo gates pass; external pilot/legal/UAT
     evidence remains pending.
