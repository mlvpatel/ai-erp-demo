# Contributor backlog

This backlog is intentionally small and safety-weighted. These are the first
issues to create after the remaining publication gates pass.

## Launch blockers

- Initialize the Git repository and verify ignored local Frappe Bench state does
  not enter history.
- Clean or exclude ignored generated artifacts before publishing any source
  archive.
- Run `scripts/check-open-source-ready.sh --release`.
- Push to a private GitHub repository first and confirm CI passes.
- Review Dependabot PR behavior against `docs/workflows/dependency-updates.md`.
- Add a short demo screenshot or GIF to the README after the local demo runbook
  is verified from a fresh clone.

## Good first issues after licensing

These should avoid money, stock, permissions, payroll, compliance, and AI
approval side effects.

The machine-readable seed list is `config/first-public-issues.json`. Keep this
section, the manifest, and `.github/labels.json` aligned before creating public
GitHub issues.

| Area | Issue idea | Acceptance check |
| --- | --- | --- |
| Docs | Add a screenshot-assisted local demo walkthrough. | `docs/runbooks/local-demo.md` and `docs/runbooks/demo-script.md` stay accurate and no secrets appear in images. |
| Docs | Improve glossary for service operations and Frappe terms. | New terms link to implemented DocTypes or ERPNext concepts. |
| Docs | Add a filled example for the industry-pack design template. | The example is clearly marked as illustrative and does not claim a new implemented industry pack. |
| Tests | Add a negative test for the next approved AI proposal type before implementing it. | Contract tests still pass and unsupported action fields are rejected. |
| Fixtures | Add more synthetic demo service locations. | Seed remains idempotent and contains no real customer data. |
| Product | Turn one roadmap item into a GitHub issue with acceptance criteria. | Issue references `ROADMAP.md` and the relevant safety boundary. |
| Developer tooling | Add optional screenshot/media links to `scripts/dev.sh demo-info` after README media exists. | The command still avoids printing secrets and `scripts/dev.sh help` documents it. |

## Maintainer-review issues

These are useful next steps, but they need careful review because they touch ERP
transaction boundaries or AI governance.

- Add the next AI proposal type, such as overdue-invoice reminder draft.
  Use `.github/ISSUE_TEMPLATE/ai_workflow.md` and
  `docs/security/ai-workflow-review.md` before design.
- Add a distribution or light-manufacturing discovery spike.
- Add integration-adapter scaffolding under `apps/ai_erp_connectors/`.
- Add an end-to-end browser smoke test for the service workflow.
- Build an executable synthetic performance harness from
  `tests/performance/service-operations-load-profile.example.json` before
  making performance claims.
- Add production deployment hardening after a real hosting target is chosen.

## Suggested labels

- `good first issue`: safe, small, contributor-friendly.
- `documentation`: docs-only or example-only.
- `discovery`: needs workflow evidence before design.
- `erp-safety`: touches money, stock, permissions, payroll, compliance, or
  auditability.
- `ai-safety`: touches AI proposal policy, prompts, citations, model behavior,
  or approval paths.
- `industry-pack`: changes or proposes vertical workflow behavior.
- `contract`: changes versioned API or event schemas.
- `blocked-license`: requires maintainer review of a license or contribution-policy concern.

## Rule of thumb

If a change can create, submit, cancel, reverse, approve, or hide an ERP record,
it is not a first issue. It needs maintainer design review, a test plan, and an
explicit safety boundary.

Use `docs/workflows/issue-triage.md` to classify backlog items before turning
them into public GitHub issues.
