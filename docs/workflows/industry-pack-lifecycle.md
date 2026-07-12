# Industry pack lifecycle

Industry expansion must move through planned → reserved → implemented. This
keeps AI ERP Demo useful for many industries without claiming unfinished packs
or generating speculative Frappe apps.

## Statuses

### Planned

A planned pack is a roadmap hypothesis.

- Do not generate a Frappe app for a planned pack.
- Keep `app_path` as `null` in `config/industry-packs.json`.
- Name one first proof workflow and the ERPNext modules likely to be reused.
- Create a discovery brief before reserving an app folder.

### Reserved

A reserved pack has a lightweight folder under `apps/`, but no generated Frappe
app code yet.

- Reserved folders are documentation-only until discovery proves a gap that
  ERPNext configuration cannot handle safely.
- Keep only a README and planning notes in the reserved folder.
- Do not add `pyproject.toml`, `hooks.py`, `modules.txt`, DocTypes, fixtures,
  patches, or dependencies until the entry gate is met.
- Keep AI behavior draft-only: retrieve, classify, summarize, explain, or draft
  for human review.

### Implemented

An implemented pack has generated Frappe app code and a demo-quality proof
workflow.

- An implemented pack must have an end-to-end demo workflow.
- The first workflow must include permissions, approval boundaries, synthetic
  fixtures, and tests for the highest-risk ERP transaction path.
- AI remains draft-only and must not directly post financial, stock, payroll,
  access-control, or compliance changes.
- Add or update contracts before introducing external APIs or business events.

## Transition gates

### Planned → reserved

Before reserving an app folder:

1. Copy `docs/product/industry-pack-design-template.md` into `docs/discovery/`.
2. Identify the target user, business job, first proof workflow, ERPNext reuse
   map, and custom behavior that configuration cannot cover.
3. Confirm fixture data is synthetic and does not require customer exports.
4. Update `config/industry-packs.json`, `docs/product/industry-pack-roadmap.md`,
   and the reserved app README together.

### Reserved → implemented

Before generating app code:

1. Confirm the discovery brief is complete enough to reject or implement the
   pack.
2. Write tests or acceptance checks for the first workflow and risky boundary.
3. Confirm the app depends on `ai_erp_core` only where shared AI proposal,
   audit, or permission behavior is needed.
4. Keep upstream ERPNext/Frappe unmodified.
5. Run `python3 scripts/check-industry-pack-lifecycle.py` and
   `scripts/run-quality-gates.sh`.

### Implemented → demo-quality

Before calling a pack demo-quality:

1. A fresh local site can install the pack using documented commands.
2. The first workflow passes an integration test.
3. The README explains the workflow in business language.
4. AI proposals are cited, immutable, and human-reviewed.
5. Public claims describe the implemented workflow separately from future packs.
