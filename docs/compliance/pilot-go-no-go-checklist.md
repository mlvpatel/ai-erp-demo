# Pilot support, incident, and go/no-go checklist

Status: human gate index for a future production pilot. Completing rows in a
private evidence system does not, by itself, make the repository GDPR
compliant, legally approved, or production ready.

Local synthetic demo may proceed without these sign-offs
(`config/pilot-readiness.json` demo_state). Real data and AWS apply remain
blocked until the accountable owner records go.

## Support ownership

| Gate | Private evidence reference | Owner name | Date | Status |
| --- | --- | --- | --- | --- |
| Named support contact for pilot tenants |  |  |  | pending |
| On-call / escalation path documented privately |  |  |  | pending |
| Bug vs security intake agreed (`SUPPORT.md`, `SECURITY.md`) |  |  |  | pending |

Public repo support text: `SUPPORT.md`. It states this project is not production
support for hosted operations.

## Incident readiness

| Gate | Private evidence reference | Owner name | Date | Status |
| --- | --- | --- | --- | --- |
| Incident runbook reviewed for pilot scope |  |  |  | pending |
| Secret-rotation and containment contacts listed privately |  |  |  | pending |
| Breach triage path supports controller notification timing where applicable |  |  |  | pending |
| Tabletop or rehearsal notes stored privately |  |  |  | pending |

Runbook: `docs/runbooks/incident-response.md`. GDPR gate row for breach
response: `docs/compliance/eu-italy-gdpr-readiness.md`.

## Legal and privacy package

| Gate | Template / gate doc | Private evidence reference | Owner name | Date | Status |
| --- | --- | --- | --- | --- | --- |
| Privacy / data-flow inventory reviewed against live tenant | `privacy-data-flow-inventory.md` |  |  |  | pending |
| Controller, processors, purposes, legal basis, RoPA | `eu-italy-gdpr-readiness.md` |  |  |  | pending |
| DPA / subprocessor / transfer review | `dpa-template.md` |  |  |  | pending |
| DPIA / LIA decision | `dpia-template.md` |  |  |  | pending |
| Italian counsel or DPO review (if Italy in scope) | `eu-italy-gdpr-readiness.md` |  |  |  | pending |
| Retention / deletion schedule approved | `eu-italy-gdpr-readiness.md` |  |  |  | pending |

## Operations and UAT (still external)

| Gate | Pointer | Private evidence reference | Owner name | Date | Status |
| --- | --- | --- | --- | --- | --- |
| Design-partner validation | `docs/discovery/design-partner-validation-template.md` |  |  |  | pending |
| Human UAT | `docs/runbooks/service-operations-synthetic-uat.md` |  |  |  | pending |
| Restore and deletion drill | `docs/runbooks/backup-restore.md` |  |  |  | pending |
| Capacity profile | Phase 7C in pending roadmap |  |  |  | pending |
| Deployment evidence (no apply without approval) | `docs/architecture/aws-production-reference.md` |  |  |  | pending |

## Accountable go/no-go

Record the decision privately. Do not commit customer names, counsel opinions,
or signature images.

| Field | Value (private) |
| --- | --- |
| Pilot name / tenant code |  |
| Decision (go / no-go / defer) |  |
| Decision date (UTC) |  |
| Accountable owner name |  |
| Conditions or blockers |  |
| Private evidence pack reference |  |

When decision is go, update the private release evidence pack first. Only then
may an authorized maintainer change `config/pilot-readiness.json` release_state
fields, and only with matching reviewed evidence. Until that happens,
`pilot_approved` stays false and forbidden claims in that manifest remain
binding.
