# Data protection impact assessment template (for counsel / DPO)

Status: **template only**. Not a completed DPIA. Not a LIA. Not approval to
process real personal data.

A future pilot that sends personal data to an AI provider or hosts real tenant
data may need a DPIA under GDPR Articles 35/36 (and any Italy-specific
guidance). Counsel or a DPO owns that determination. Keep completed DPIA text,
risk scores, and signatures out of Git.

## How to use

1. Confirm whether a DPIA is required for the planned pilot scope.
2. If required, complete the sections below in a private document management
   system using this outline.
3. Link the private artifact from
   `docs/compliance/service-operations-pilot-evidence-template.md`.
4. Do not flip `config/pilot-readiness.json` legal gates until counsel records
   the decision.

## Screening (complete privately)

- Will the pilot process real (non-synthetic) personal data?
- Will personal data leave the ERP tenant to an external model provider?
- Will special-category data, systematic monitoring, or large-scale profiling
  occur?
- Counsel/DPO DPIA-required decision (yes / no / deferred):
- Screening date and private reference:

## Context of processing (draft facts for counsel)

| Topic | Demo/repo fact | Pilot value (private) |
| --- | --- | --- |
| Product | Governed field-service ERP demo on ERPNext/Frappe |  |
| Controllers / processors | Not appointed in-repo |  |
| Data subjects | Synthetic seed users and customers only in demo |  |
| Personal data categories | See `privacy-data-flow-inventory.md` |  |
| Recipients | Local operators; optional OpenAI adapter when enabled |  |
| Retention | Disposable local demo; pilot schedule unapproved |  |
| AI boundary | Proposal-only; ERP posts via deterministic code + humans |  |

## Necessity and proportionality (questions for counsel)

1. What legitimate interest or other legal basis applies to each purpose?
2. Can the same operational benefit be achieved with synthetic data or stricter
   minimization?
3. Are role permissions (technician vs manager vs accounts) sufficient for the
   pilot tenant?
4. Is provider retention (`store=false` and DPA terms) adequate for the risk?

## Risk register (blank for private completion)

| Risk ID | Description | Likelihood | Impact | Existing control in repo | Residual risk | Treatment owner |
| --- | --- | --- | --- | --- | --- | --- |
|  | Unauthorized finance visibility |  |  | Authorization matrix, technician field hiding |  |  |
|  | PII in provider request |  |  | Minimize + `safety.redact` |  |  |
|  | Autonomous ERP mutation by AI |  |  | Proposal-only ledger; AI cannot post |  |  |
|  | Secrets in Git/CI |  |  | Publication secret scan, quality gates |  |  |
|  | Cross-tenant leakage |  |  | Site isolation checks |  |  |
|  | Incomplete erasure after restore |  |  | Backup/restore runbook; drill pending |  |  |

Add rows privately as needed. Do not invent residual-risk scores in Git.

## Measures planned before real data

- Named support and incident owners (`SUPPORT.md`,
  `docs/runbooks/incident-response.md`, go/no-go checklist).
- Executed DPA / transfer review (`dpa-template.md`).
- Retention, deletion, and backup drill evidence.
- Human UAT and design-partner validation records.
- Live provider evaluation only with synthetic or approved redacted inputs.

## Sign-off (private; do not commit signatures)

| Role | Name | Date | Private evidence reference | Decision |
| --- | --- | --- | --- | --- |
| DPO or privacy counsel |  |  |  |  |
| Security reviewer |  |  |  |  |
| Accountable pilot owner |  |  |  |  |

Decision values when complete: DPIA not required / DPIA approved / DPIA rejected
/ deferred. Leave rows blank in Git.
