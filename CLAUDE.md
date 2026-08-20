# Claude Code entry point

Read these before changing anything:

1. `AGENTS.md`: repository working rules (root entrypoint; details in
   `.agents/AGENTS.md`).
2. `.agents/skills/erp-build-and-minimal-change/SKILL.md`: surgical custom-app
   and control-plane change ladder.
3. `.agents/skills/ai-governance-and-gates/SKILL.md`: AI proposal boundary and
   quality-gate enforcement.
4. `.agents/skills/behuman/SKILL.md`: BEhuMan prose rules (always on for docs,
   commit messages, summaries, and other written deliverables).
5. `docs/workflows/quality-gates.md`: which gate to run for which change.
6. `docs/product/demo-version-loop.md` and `docs/product/demo-version-stack.md`
   (Demo Version path + pin-accurate stack; `config/demo-version.json`).

Other skills under `.agents/skills/` cover discovery, security/PII, connectors,
architecture, QA, and tech-stack constraints. When `.claude/skills/` is present
locally it mirrors the same set for Claude Code. Cursor loads the same
`behuman` skill from `.cursor/skills/behuman/` plus the always-on rule
`.cursor/rules/behuman.mdc`.

## Hard rules

- Default commit identity: `mlvpatel <mlvpatel@users.noreply.github.com>`
  (author and committer). Owner may set author to
  `Cursor Agent <cursoragent@cursor.com>` for GitHub Contributors credit;
  committer stays mlvpatel. No AI/LLM/bot trailers in commit messages.
- Never claim production ready, human UAT approved, legally approved, GDPR
  compliant, or full multi-industry ERP without separate recorded evidence.
  Demo legal-readiness artifacts live under `docs/compliance/` (owner
  fill-in checklist and templates); they are not counsel sign-off.
- AI is proposal-only: it must never post accounting, stock, payroll,
  permissions, compliance records, or customer messages. Deterministic ERP
  code and authorized humans change business state.
- Synthetic data only. No secrets, raw prompts, or raw provider responses in
  Git, tests, CI logs, or release evidence.
- Custom behavior lives in `apps/`; provider calls, prompts, retrieval, and
  evaluation live in `services/ai_control_plane/`; external APIs and events
  are versioned in `contracts/`; new services, datastores, or providers need
  an ADR in `docs/adr/` first.
- Prose follows BEhuMan (`.agents/skills/behuman/SKILL.md`): no AI-writing
  tells in docs, commit messages, or other written deliverables.

## Gates

Run the smallest relevant gate, then the broader one:

```sh
scripts/run-quality-gates.sh          # always
scripts/dev.sh control-plane-test     # control-plane or contract changes
scripts/dev.sh contract-test
scripts/dev.sh service-test           # Frappe app, permission, stock, invoice,
scripts/dev.sh e2e-test               # closeout, AI Proposal, workflow changes
```

The host Python may be older than the control plane's requirement; use the
Docker-backed `scripts/dev.sh` helpers or a `uv`-managed Python that satisfies
`services/ai_control_plane/pyproject.toml`.
