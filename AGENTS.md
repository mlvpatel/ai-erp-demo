# AI ERP Demo: agent entrypoint

Start here before changing this repository.

## Read first

1. `.agents/AGENTS.md`: repository working rules (authoritative copy).
2. `.agents/skills/erp-build-and-minimal-change/SKILL.md`: minimal-change build ladder.
3. `.agents/skills/ai-governance-and-gates/SKILL.md`: AI proposal boundary and gates.
4. `.agents/skills/behuman/SKILL.md`: BEhuMan prose rules (always on for docs,
   commit messages, summaries, and other written deliverables).
5. `docs/product/pending-roadmap-for-claude-code.md`: phase-by-phase continuation plan.
6. `docs/workflows/quality-gates.md`: which gate to run for which change.

Additional skills live under `.agents/skills/` (mirrored for Claude Code under
`.claude/skills/` and for Cursor under `.cursor/skills/` when those trees are
present locally). Cursor also loads `.cursor/rules/behuman.mdc` as an always-on
rule.

## Hard rules (summary)

- Commit only as `mlvpatel <mlvpatel@users.noreply.github.com>` (author and
  committer). No AI, LLM, bot, assistant, or generated-by attribution.
- Never claim production ready, human UAT approved, legally approved, GDPR
  compliant, or full multi-industry ERP without separate recorded evidence.
- AI is proposal-only: it must never post accounting, stock, payroll,
  permissions, compliance records, or customer messages.
- Synthetic data only. No secrets, raw prompts, or raw provider responses in
  Git, tests, CI logs, or release evidence.
- Custom behavior lives in `apps/`; provider calls, prompts, retrieval, and
  evaluation live in `services/ai_control_plane/`; external APIs and events are
  versioned in `contracts/`; new services, datastores, or providers need an ADR
  in `docs/adr/` first.
- Prose follows BEhuMan (`.agents/skills/behuman/SKILL.md` /
  `.cursor/skills/behuman/SKILL.md`): no AI-writing tells in docs, commit
  messages, or other written deliverables.

## Gates

```sh
scripts/run-quality-gates.sh          # always
scripts/dev.sh control-plane-test     # control-plane or contract changes
scripts/dev.sh contract-test
scripts/dev.sh service-test           # Frappe app, permission, stock, invoice
scripts/dev.sh e2e-test               # closeout, AI Proposal, workflow changes
```
