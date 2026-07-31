# Owner fill-in checklist

One page for the accountable owner (and counsel/DPO where marked). Agents and
contributors must not invent names, signatures, legal basis choices, partner
scores, AWS credentials, or OpenAI keys to “complete” these rows.

These files are templates and gates. Filling them in a private evidence system
does not make the product GDPR compliant, legally approved, human-UAT approved,
or production ready. Do not commit customer data, counsel opinions, contract
text, API keys, or signature images to Git. Record private references only.

Local synthetic demo can run without most of this list. Real-data pilot and AWS
apply stay blocked until the accountable owner records go on
`pilot-go-no-go-checklist.md` and matching private evidence exists.

## How to use

1. Work top to bottom. Mark each checkbox when the private artifact or named
   person exists.
2. Open the linked file and fill only the blank fields that belong there. Prefer
   private storage for anything with real names, contracts, or credentials.
3. Leave public-repo blanks empty when the answer is private. Put a short
   evidence reference on
   `service-operations-pilot-evidence-template.md` or the go/no-go tables.
4. Do not flip `config/pilot-readiness.json` release fields until private go
   evidence exists and a maintainer updates the manifest on purpose.

## Labels used below

| Label | Meaning |
| --- | --- |
| Owner only | Agent must not invent or commit a value |
| Counsel / DPO | Legal or privacy specialist owns the decision |
| Optional for demo | Not required for local synthetic Demo Version |
| Required for real-data pilot | Blocker before real personal data or AWS apply |

---

## 1. People and support

Public support text: [`SUPPORT.md`](../../SUPPORT.md) (states this project is
not production support for hosted operations). Sign-off tables:
[`pilot-go-no-go-checklist.md`](pilot-go-no-go-checklist.md) section “Support
ownership”. Incident runbook: [`docs/runbooks/incident-response.md`](../runbooks/incident-response.md).

| Done | What to provide | Where to record | Your notes (private or blank in Git) |
| --- | --- | --- | --- |
| [ ] | Named support contact for pilot tenants | `pilot-go-no-go-checklist.md` → Support ownership row 1 | Owner: ____________ Date: ____________ Ref: ____________ |
| [ ] | On-call / escalation path | Same file → Support ownership row 2 | Owner: ____________ Date: ____________ Ref: ____________ |
| [ ] | Bug vs security intake agreed | Same file → Support ownership row 3; also `SUPPORT.md` / `SECURITY.md` process | Owner: ____________ Date: ____________ |
| [ ] | Incident runbook reviewed for pilot scope | `pilot-go-no-go-checklist.md` → Incident readiness | Owner: ____________ Ref: ____________ |
| [ ] | Secret-rotation and containment contacts | Same → Incident readiness | Ref: ____________ |
| [ ] | Breach triage path (controller notification timing) | Same + `eu-italy-gdpr-readiness.md` breach row | Ref: ____________ |
| [ ] | Tabletop or rehearsal notes | Private store; reference on go/no-go | Ref: ____________ |

Label: Owner only. Required for real-data pilot. Optional for demo.

---

## 2. Privacy inventory and PII rules (review, do not invent RoPA)

Engineering inventory (synthetic demo facts only):
[`privacy-data-flow-inventory.md`](privacy-data-flow-inventory.md).
Contributor rules: [`pii-handling-notes.md`](pii-handling-notes.md).
Classification: [`docs/security/data-classification.md`](../security/data-classification.md).

| Done | What to provide | Where to record | Your notes |
| --- | --- | --- | --- |
| [ ] | Confirm demo inventory still matches the live tenant plan (systems, data classes, AI visibility) | Review `privacy-data-flow-inventory.md`; status on go/no-go “Legal and privacy package” | Reviewer: ____________ Date: ____________ |
| [ ] | Pilot retention schedule for site DB, AI Proposal rows, backups, logs, provider | Inventory “Retention intent” pilot column + `eu-italy-gdpr-readiness.md` Retention gate | Schedule ref: ____________ |
| [ ] | Acknowledge redaction is incomplete for names/addresses; synthetic discipline stays mandatory | Read `pii-handling-notes.md` (no Git fill required) | Initials: ____________ |

Label: Owner only for retention and tenant review. Templates here are not a
RoPA or lawful-basis decision. Required for real-data pilot.

---

## 3. DPA (counsel)

Template: [`dpa-template.md`](dpa-template.md). Signatures stay private.

| Done | What to provide | Where to fill / store | Your notes |
| --- | --- | --- | --- |
| [ ] | Controller legal name and notice contact | Private adaptation of DPA template “Parties” | Private only |
| [ ] | Processor / provider legal name and subprocessors | Same | Private only |
| [ ] | Effective date, governing law / venue | Same (counsel) | Private only |
| [ ] | Transfer mechanism (for example SCCs), destination regions | DPA “International transfers” + Italy/EU notes | Private only |
| [ ] | Executed signatures | DPA “Sign-off” table privately; never commit | Evidence ref: ____________ |
| [ ] | Public-safe pointer after execution | `service-operations-pilot-evidence-template.md` → DPA/subprocessor/transfer row; go/no-go legal package | Ref: ____________ Date: ____________ |

Label: Counsel / DPO + Owner. Agent cannot complete. Template ≠ executed DPA.
Required for real-data pilot when a provider processes personal data. Optional
for demo (template provider, synthetic only).

---

## 4. DPIA / LIA (counsel / DPO)

Template: [`dpia-template.md`](dpia-template.md).

| Done | What to provide | Where to fill / store | Your notes |
| --- | --- | --- | --- |
| [ ] | Screening: real personal data? provider egress? special categories? | DPIA “Screening” privately | Decision: yes / no / deferred |
| [ ] | Counsel/DPO “DPIA required?” decision + date | Same | Ref: ____________ |
| [ ] | Controllers/processors, data subjects, categories, retention for the pilot | DPIA “Context of processing” pilot column | Private only |
| [ ] | Legal basis / necessity answers | DPIA “Necessity and proportionality” | Private only |
| [ ] | Risk register residual scores and treatments | DPIA “Risk register” (leave Git blanks) | Private only |
| [ ] | Sign-off (DPO/counsel, security, accountable owner) | DPIA “Sign-off” privately | Evidence ref: ____________ |
| [ ] | Public-safe pointer | Pilot evidence template + go/no-go DPIA row | Ref: ____________ Date: ____________ |

Label: Counsel / DPO + Owner. Agent cannot complete. Template ≠ completed DPIA.
Required for real-data pilot when counsel says a DPIA is needed.

---

## 5. EU / Italy GDPR readiness gates

Gate table: [`eu-italy-gdpr-readiness.md`](eu-italy-gdpr-readiness.md).
Hosting target noted there is AWS `eu-central-1`; that note is not transfer
approval and not a GDPR compliance claim.

| Done | Gate (copy from readiness doc) | Private evidence you must supply | Ref / owner / date |
| --- | --- | --- | --- |
| [ ] | Roles and purposes | Named controller, processors, purposes, categories, subjects, legal basis, RoPA | ____________ |
| [ ] | Minimization | Field-level map; unnecessary exports disabled | ____________ |
| [ ] | Transparency and rights | Privacy notice + rights workflow and response owner | ____________ |
| [ ] | Retention | Approved retention/deletion schedule | ____________ |
| [ ] | Security | Access review, MFA, encryption, IR, restore drill, supplier review | ____________ |
| [ ] | AI provider | DPA, transfer, DPIA/LIA, EU project eligibility, residency/retention | ____________ |
| [ ] | Breach response | Triage path supporting applicable notification timing | ____________ |
| [ ] | Italy-specific review (if Italy in scope) | Italian counsel/DPO on Garante, monitoring, sector, tax retention, language | ____________ |
| [ ] | Pilot acceptance | Named tenant, roles, UAT, capacity, support, RPO/RTO, rollback, deletion rehearsal | ____________ |

Also mark the matching rows in `pilot-go-no-go-checklist.md` → Legal and privacy
package. Label: Owner + Counsel. Required for real-data pilot. Not a claim that
the demo is GDPR compliant.

---

## 6. Design-partner validation and human UAT

Validation worksheet:
[`docs/discovery/design-partner-validation-template.md`](../discovery/design-partner-validation-template.md).
Facilitator steps: [`docs/runbooks/design-partner-facilitator.md`](../runbooks/design-partner-facilitator.md).
Synthetic UAT rehearsal:
[`docs/runbooks/service-operations-synthetic-uat.md`](../runbooks/service-operations-synthetic-uat.md).

| Done | What to provide | Where to fill | Your notes |
| --- | --- | --- | --- |
| [ ] | Session setup: partner, segment, size, roles, date, facilitator | Design-partner template “Session setup” | Leave blank until the session runs |
| [ ] | Discovery gate answers | Same → “Discovery gate” | ____________ |
| [ ] | Workflow scores 1–10 (partner-rated; do not invent) | Same → “Workflow validation” | ____________ |
| [ ] | AI safety observed results | Same → “AI safety validation” | ____________ |
| [ ] | 9/10 decision fields after partner rates | Same → “9/10 decision” | Approver: ____________ |
| [ ] | Repository-safe sanitized summary only | Same → “Repository-safe summary” | No real PII in Git |
| [ ] | Human UAT evidence (beyond automated suites) | Synthetic UAT runbook + go/no-go “Operations and UAT” | Ref: ____________ |
| [ ] | Pointer on pilot evidence index | `service-operations-pilot-evidence-template.md` design-partner + UAT rows | Ref: ____________ |

Label: Owner / facilitator. Agent must not invent partner scores or flip the
scorecard to 9. Required for real-data pilot acceptance story. Optional for
demo packaging.

---

## 7. Product and pilot decisions

Accountable decision:
[`pilot-go-no-go-checklist.md`](pilot-go-no-go-checklist.md) → “Accountable
go/no-go”. Public-safe index:
[`service-operations-pilot-evidence-template.md`](service-operations-pilot-evidence-template.md).
Manifest (do not flip casually): `config/pilot-readiness.json`.

| Done | What to provide | Where to record | Your notes |
| --- | --- | --- | --- |
| [ ] | Pilot name / tenant code | Go/no-go “Accountable go/no-go” (private) | ____________ |
| [ ] | Decision: go / no-go / defer | Same | Decision: ____________ |
| [ ] | Decision date (UTC) | Same | ____________ |
| [ ] | Accountable owner name | Same | ____________ |
| [ ] | Conditions or blockers | Same | ____________ |
| [ ] | Private evidence pack reference | Same + pilot evidence template | ____________ |
| [ ] | Role mapping and finance segregation for the pilot tenant | Pilot evidence “Human and legal approvals” | Ref: ____________ |
| [ ] | Capacity / concurrency profile | Go/no-go Operations row; private evidence | Ref: ____________ |
| [ ] | Restore and deletion drill | `docs/runbooks/backup-restore.md` + go/no-go | Ref: ____________ |
| [ ] | Only after private go: maintainer updates `config/pilot-readiness.json` | Manifest release_state fields | Maintainer: ____________ |

Label: Owner only. Agent cannot record go. Forbidden claims in the manifest
remain binding until evidence matches.

---

## 8. Optional credentials and live evaluation (owner / operator)

Do not ask an agent to supply AWS or OpenAI secrets. Default demo uses
`AI_ERP_PROVIDER=template` with no key.

Live-eval ack and operator steps:
[`docs/runbooks/openai-live-evaluation.md`](../runbooks/openai-live-evaluation.md).
AWS reference (no apply without approval):
[`docs/architecture/aws-production-reference.md`](../architecture/aws-production-reference.md).

| Done | What to provide | Where / how | Your notes |
| --- | --- | --- | --- |
| [ ] | Decide whether live OpenAI eval is in scope for this pilot | Product decision; keep template provider if not | In scope? yes / no |
| [ ] | `OPENAI_API_KEY` from approved secret store only (never Git, issues, screenshots) | Private deployment task env | Store path: ____________ |
| [ ] | Non-secret gates: `AI_ERP_PROVIDER=openai`, `OPENAI_API_KEY_SOURCE=deployment-secret-store`, `AI_ERP_ENABLE_PRIVATE_LIVE_EVAL=I_ACKNOWLEDGE_SYNTHETIC_ONLY` | Live-eval runbook “Operator unblock checklist” | Set in private task only |
| [ ] | Pinned EU base URL and model from ADR-0006 | Same runbook | Confirmed: [ ] |
| [ ] | Project-level hard budget and alert before the run | OpenAI project / billing (private) | ____________ |
| [ ] | Private deployment/task environment (not public CI) | Same | ____________ |
| [ ] | Store only safe aggregate stdout (`PASS` / `FAIL` / `DRY_RUN` line) | Private evidence; never prompts/responses | Ref: ____________ |
| [ ] | AWS account, OIDC, domain/certs, budget (if hosting) | Private; plan review on AWS reference + go/no-go deployment row | Ref: ____________ |

Label: Owner / operator only. Optional for demo. Required only if you choose
live provider evaluation or AWS apply. A live-eval PASS is technical evidence,
not approval for real data.

Credential-free prep (no key, never records PASS):

```sh
export AI_ERP_PROVIDER=openai
export AI_ERP_ENABLE_PRIVATE_LIVE_EVAL=I_ACKNOWLEDGE_SYNTHETIC_ONLY
python -m ai_erp_control_plane.live_eval --dry-run
```

---

## 9. Optional demo content (synthetic only)

Keep media and partner notes free of real personal data
(`pii-handling-notes.md`). Suggested synthetic media paths are listed in the
design-partner template.

| Done | What to provide | Where | Your notes |
| --- | --- | --- | --- |
| [ ] | Extra synthetic screenshots or walkthrough clips (optional) | `docs/media/demo/` if public-safe | Paths: ____________ |
| [ ] | Sanitized design-partner summary suitable for Git (optional) | Design-partner “Repository-safe summary” | ____________ |
| [ ] | Facilitator dry-run notes without inventing partner scores (optional) | `docs/runbooks/design-partner-dry-run-notes.md` | ____________ |

Label: Optional for demo. Synthetic or approved-redacted only.

---

## File map (quick index)

| File | Role |
| --- | --- |
| [`README.md`](README.md) | Package index and claim boundaries |
| [`privacy-data-flow-inventory.md`](privacy-data-flow-inventory.md) | Synthetic data classes and AI visibility |
| [`pii-handling-notes.md`](pii-handling-notes.md) | Code-aligned redaction rules |
| [`dpa-template.md`](dpa-template.md) | Counsel DPA outline |
| [`dpia-template.md`](dpia-template.md) | Counsel/DPO DPIA outline |
| [`eu-italy-gdpr-readiness.md`](eu-italy-gdpr-readiness.md) | Gate table before real pilot data |
| [`pilot-go-no-go-checklist.md`](pilot-go-no-go-checklist.md) | Support, incident, legal, UAT, go/no-go |
| [`service-operations-pilot-evidence-template.md`](service-operations-pilot-evidence-template.md) | Public-safe evidence references |
| [`../discovery/design-partner-validation-template.md`](../discovery/design-partner-validation-template.md) | Partner session scores |
| [`../../SUPPORT.md`](../../SUPPORT.md) | Public support scope |
| [`../runbooks/openai-live-evaluation.md`](../runbooks/openai-live-evaluation.md) | Live-eval ack and secret rules |
| `config/pilot-readiness.json` | Demo vs pilot manifest (maintainer) |

## What agents must not do

- Fill owner, counsel, partner, or go/no-go fields with invented people or dates.
- Claim GDPR compliant, production ready, human UAT approved, or legally
  approved from templates alone.
- Commit AWS credentials, OpenAI keys, raw prompts, raw provider responses, or
  signed contract text.
- Treat a dry-run live eval or template-provider demo as live-model quality
  evidence.
