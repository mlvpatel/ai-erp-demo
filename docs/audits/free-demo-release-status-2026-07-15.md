# Zero-cost local demo release status — 2026-07-15

This is the current release record for the private, local, synthetic field-service
demo. It replaces the production-pilot audit as the active milestone without
changing or deleting the production infrastructure reference.

## Release boundary

- Runtime: local Docker Compose only.
- Data: synthetic fixtures only.
- AI: deterministic `template` provider; no hosted-model quality claim.
- Implemented industry: field service.
- Configured demos: distribution and light manufacturing.
- Excluded: AWS apply, live OpenAI, real customer data, production capacity and
  recovery evidence, human UAT, legal approval, support ownership, and pilot
  go/no-go.

## Evidence required on the final release commit

| Evidence | Status |
| --- | --- |
| Static repository quality gates | Pass on release working tree |
| Strict publication-source check from a clean checkout | Required after commit; record on PR #6 |
| Full Docker behavior, performance-smoke, and browser gates | Pass on release working tree |
| Three sanitized synthetic UI screenshots | Pass visual review, format check, and publication secret scan |
| Private GitHub checks | Required after push; record on PR #6 |
| Maintainer approval to mark PR ready and merge | Pending explicit approval |

The working-tree run passed 21 control-plane tests, 11 contract tests, 8 core
and configured-demo integration tests, 14 service integration tests, 5
performance helper tests, the scaled synthetic performance smoke, and all 5
Playwright journeys. The prior commit `9133f61` passed all six GitHub checks and
a strict clean-copy publication-source check. Exact-commit clean-copy and
GitHub results are recorded on PR #6 after push so this committed file does not
create a self-invalidating evidence loop.

## Deferred production boundary

`config/pilot-readiness.json` remains the machine-readable authority. Its
production deployment, human-approval, and pilot-approval flags remain false.
This demo must not be described as production ready, GDPR compliant, human-UAT
approved, or a complete multi-industry ERP.
