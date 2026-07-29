# EU/Italy GDPR readiness gate

- Status: engineering template; human/legal approval pending
- Hosting target: AWS `eu-central-1`
- Pilot data default: synthetic only

EU hosting alone does not establish GDPR compliance. Before real pilot data,
the controller must approve and privately retain evidence for every gate below.

| Gate | Required private evidence | Owner/status |
| --- | --- | --- |
| Roles and purposes | Named controller, processors/subprocessors, purposes, categories, data subjects, legal basis, and RoPA entry. | Human owner required |
| Minimization | Field-level data map for ERP, files, backups, logs, AI prompts, support, and analytics; unnecessary exports disabled. | Human owner required |
| Transparency and rights | Privacy notice plus authenticated access, export, correction, restriction, objection, and deletion workflow with response owner. | Human owner required |
| Retention | Approved retention/deletion schedule for ERP records, audit evidence, logs, AI provider data, files, backups, and support artifacts. | Human owner required |
| Security | Access review, MFA, least privilege, encryption, key rotation, incident response, monitoring, restore drill, and supplier review evidence. | Deployment evidence required |
| AI provider | DPA, subprocessor and transfer review, DPIA/LIA decision, EU project eligibility, data-residency/processing setting, and retention/abuse-monitoring control. | Legal + OpenAI account approval required |
| Breach response | Private triage path, controller notification workflow, evidence preservation, and assessment supporting the GDPR 72-hour notification window where applicable. | Human owner required |
| Italy-specific review | Counsel/DPO review of Italian Garante requirements, employee monitoring, sector rules, tax/accounting retention, and language/notice needs. | Italian counsel required |
| Pilot acceptance | Named tenant, roles, UAT sign-off, capacity evidence, support/on-call owner, RPO/RTO, rollback, and deletion rehearsal. | Pilot owner required |

## AI data flow

The service-closeout workflow sends only subject, status, description, closeout
notes, typed time facts without technician identity, and part facts without
warehouse identity. Tenant, user, work-order, source-record, hash, technician,
and warehouse identifiers stay out of the provider request. The call uses no
tools and `store=false`; policy and citations are constructed locally. This is
data minimization, not a substitute for a lawful basis or provider agreement.

## Rights and erasure runbook

1. Authenticate the requester and confirm controller scope.
2. Locate the tenant site, files, AI Proposal audit records, operational logs,
   support records, and backup schedule without crossing tenant boundaries.
3. Classify each record as correctable, erasable, restricted, or retained under
   a documented legal obligation. Do not let AI decide this classification.
4. Execute approved changes using deterministic ERP/admin procedures and record
   the operator, basis, scope, and timestamp privately.
5. Prevent erased data from being reintroduced during restore; document how
   backup expiry or post-restore re-erasure satisfies the approved schedule.
6. Send the controller-approved response and retain only necessary evidence.

## Related templates

- Data-flow inventory: `docs/compliance/privacy-data-flow-inventory.md`
- DPA outline for counsel: `docs/compliance/dpa-template.md`
- DPIA outline for counsel/DPO: `docs/compliance/dpia-template.md`
- Human go/no-go index: `docs/compliance/pilot-go-no-go-checklist.md`
- PII engineering notes: `docs/compliance/pii-handling-notes.md`

## Launch decision

Real data remains blocked until every row has a named owner, approved evidence,
and review date. Record approval outside the public repository; do not commit
names, customer records, contracts, DPIAs, keys, screenshots, or audit exports.
