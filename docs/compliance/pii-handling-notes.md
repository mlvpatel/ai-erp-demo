# PII handling notes (aligned to current code)

Status: engineering notes for contributors. Not a privacy policy and not GDPR
compliance.

Companion inventory: `docs/compliance/privacy-data-flow-inventory.md`.
Classification policy: `docs/security/data-classification.md`.

## Rules that match the code today

1. Synthetic data only for demo seed, fixtures, screenshots, and CI.
2. AI remains proposal-only (ADR-0003). Review of an AI Proposal does not post
   stock, invoices, payroll, permissions, compliance state, or customer email.
3. Before an OpenAI provider call, closeout and repair-memory paths minimize
   identifiers and call `redact()` in
   `services/ai_control_plane/src/ai_erp_control_plane/safety.py`.
4. Template renderers use `quote_inline` / `quote_block` so free-text notes are
   redacted and instruction-like spans are neutralized before `draft_content`
   is stored.
5. Audit metadata may include `redaction_count` and content hashes. Raw prompt
   and raw provider response bodies must not land in Git, public CI logs, or
   release evidence.
6. Publication and quality gates scan for secrets
   (`scripts/check-publication-secrets.py`, `scripts/run-quality-gates.sh`).
7. Tenant isolation is site-based (ADR-0002); retrieval must stay
   permission-scoped.

## What `redact()` currently covers

Implemented patterns in `safety.py`:

- Email shapes
- Phone-like digit runs (dates and money-shaped grounding facts kept)
- Credential-shaped tokens (`api_key`, `password`, `bearer`, and similar)

Not a complete PII detector. Names, free-form addresses, and novel secret
formats can still slip through if operators paste them into allow-listed text
fields. Minimization and synthetic-data discipline remain mandatory.

## Contributor checklist before adding AI or fixtures

- Prefer synthetic values that are obviously fake.
- Do not add real phone numbers, emails, national IDs, or API keys to fixtures.
- Extend allow-lists only with an ADR when new fields must reach a provider.
- Add a focused test when changing redaction or minimize behavior
  (`services/ai_control_plane/tests/`, contract tests).
- Run `scripts/check-ai-data-boundary.py` when touching AI data-boundary config.
- Keep screenshots and partner notes free of real personal data.

## Incident path if PII or secrets escape

Follow `docs/runbooks/incident-response.md`: stop spreading the material, notify
the owner privately, rotate secrets, scrub working trees, and add a regression
check when the leak path can recur.
