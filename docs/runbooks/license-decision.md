# License decision runbook

This runbook records the accepted ADR-0005 decision and keeps future license
changes coherent. It is not legal advice; confirm material policy changes with
counsel before public release when needed.

## Current state

- `AGPL-3.0-only` is selected for repository-owned code.
- Both custom Frappe apps declare `app_license = "agpl-3.0"` and carry matching
  package, README, and copyright metadata.
- The AI control plane package declares `AGPL-3.0-only`.
- DCO sign-off is required for contributions.
- Upstream ERPNext and Frappe retain their own GPL-3.0 and MIT licenses.

## Decision record

Selected: `AGPL-3.0-only`. This protects source availability for modified
network-hosted versions while remaining compatible with the GPLv3 ERPNext
boundary. The alternatives below remain historical context for future review.

### Alternatives considered

| Option | Good fit when | Main trade-off |
| --- | --- | --- |
| MIT-style permissive | You want maximum reuse, low friction, and simple compatibility for a demo or service-business toolkit. | Others can use the code in closed products with minimal obligations. |
| AGPL-3.0 | You want a stronger open-core/SaaS protection story, matching the supplied MVP blueprint's recommendation. | More legal and compatibility review is needed, and some companies avoid AGPL dependencies. |
| GPL-3.0-compatible policy | You want stronger copyleft while staying close to ERPNext's GPL-3.0 ecosystem. | SaaS/network-use obligations differ from AGPL; still needs compatibility review. |
| Split license | You want different policies for apps, docs, examples, and the AI control plane. | Contributors need very clear boundaries and every package must advertise the correct license. |

## Future policy-review questions

Answer these before any future license or contribution-policy change:

1. Is the goal community adoption with minimal friction, or protection against
   closed hosted competitors?
2. Will the project be offered as managed SaaS, implementation toolkit, or
   mostly local/self-host demo?
3. Should future external contributors sign a CLA or DCO?
4. Does the chosen license align with ERPNext, Frappe, and any future hosted
   distribution plan?
5. Who owns the copyright line: individual, company, or future foundation?
6. What public contact email should replace `opensource@ai-erp.example`?

For a structured local checklist, copy:

```bash
cp config/owner-decisions.example.json config/owner-decisions.local.json
python3 scripts/check-owner-decisions.py --strict
```

`config/owner-decisions.local.json` is ignored by Git. It is a local planning
file only and must not be included in manual source archives; after the
decisions are final, apply them to the public files listed below and rerun the
release checks.

## Reconciliation checklist

The accepted decision updated all of these together; use the same set for any
future policy change:

- Root `LICENSE` with the chosen license text.
- `README.md` root license note.
- `docs/adr/0005-root-license-required-before-github-publish.md` status and
  decision text.
- `apps/ai_erp_core/license.txt`.
- `apps/ai_erp_service/license.txt`.
- `apps/ai_erp_core/ai_erp_core/hooks.py` `app_license`.
- `apps/ai_erp_service/ai_erp_service/hooks.py` `app_license`.
- `apps/ai_erp_core/README.md` license section.
- `apps/ai_erp_service/README.md` license section.
- `apps/ai_erp_core/pyproject.toml` author/contact metadata, and license
  metadata if the packaging standard used by Frappe supports it cleanly.
- `apps/ai_erp_service/pyproject.toml` author/contact metadata, and license
  metadata if the packaging standard used by Frappe supports it cleanly.
- `services/ai_control_plane/pyproject.toml` license metadata and contact
  metadata if the service is distributed as a Python package.
- `CONTRIBUTING.md` if a CLA, DCO, or contribution-signoff policy is selected.

## Verification

Run these after editing:

```bash
scripts/check-open-source-ready.sh --release
python3 scripts/check-owner-decisions.py --strict
python3 scripts/check-license-metadata.py --strict
scripts/run-quality-gates.sh
```

Then run the Docker-backed demo checks from
`docs/workflows/quality-gates.md` before creating a public release tag.

## Do not do

- Do not mix a root license with contradictory app-level license text.
- Do not leave `[year]`, `[fullname]`, or `opensource@ai-erp.example` in
  release metadata.
- Do not accept external contributions before the public license policy is
  visible.
- Do not paste production contracts, customer data, or private legal advice
  into the repository.
