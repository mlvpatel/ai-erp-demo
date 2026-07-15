# Contributor backlog

This backlog is safety-weighted. The current release target is a zero-cost,
local, synthetic demo. Human and billable production-pilot gates are deferred
and do not block that demo.

## Zero-cost demo release

- Re-run the clean-checkout static and Docker-backed demo gates after the
  release documentation and media are finalized.
- Keep the screenshot-assisted local demo walkthrough described by
  `docs/runbooks/demo-script.md` synchronized with the verified synthetic
  workflow whenever visible behavior changes.
- Refresh private PR #6 with current evidence and require green checks on its
  final commit.
- Mark the pull request ready and merge only after explicit maintainer approval.

## Deferred production-pilot evidence

- Obtain protected AWS/OpenAI credentials, domain/certificate configuration,
  reviewed recurring cost, and explicit billable-operation approval.
- Build, scan, sign, and verify production images by digest.
- Run protected foundation/activation, authenticated smoke, live OpenAI
  evaluation, exact capacity, backup, isolated restore, deletion, and rollback
  drills; retain private evidence.
- Complete design-partner validation, human UAT, legal/DPA/DPIA review, named
  support ownership, and accountable go/no-go.

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
- Validate the configured distribution and light-manufacturing demos with design partners before promoting either pack to implemented.
- Add integration-adapter scaffolding under `apps/ai_erp_connectors/`.
- Run the tracked full-profile load contract on approved pilot infrastructure
  and retain private capacity evidence with the protected
  `production-capacity.yml` workflow. The exact-volume runner and authenticated ten-request/
  five-user concurrency gate are implemented, but remain unexecuted until the
  billable pilot is authorized. The local `SMOKE_PASS_NOT_FULL_PROFILE` result
  cannot support a public capacity claim.
- Cost-review and apply the implemented ADR-0007 AWS foundation only after the
  account, budget, domain, RPO/RTO, support owner, and legal/data gates are approved.

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
