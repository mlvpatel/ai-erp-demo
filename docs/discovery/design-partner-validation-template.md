# Design Partner Validation Template

Use this template to validate the field-service 9/10 target with synthetic or
approved redacted examples only. Do not commit customer names, employee names,
addresses, phone numbers, emails, private attachments, credentials, production
exports, or raw AI prompts and responses.

Leave score cells blank until the partner session runs. Do not invent partner
scores, UAT approval, or production readiness claims from a dry rehearsal.

**Facilitator runbook (step-by-step):**
[`docs/runbooks/design-partner-facilitator.md`](../runbooks/design-partner-facilitator.md)

## Facilitator prep (structural only)

Follow the facilitator runbook end-to-end before the partner arrives. Short
path:

```sh
scripts/dev.sh demo-info
scripts/dev.sh up
scripts/dev.sh bootstrap    # first run or after pin/app changes
# separate terminal: scripts/dev.sh bench-start
scripts/dev.sh seed-demo
scripts/dev.sh demo-check
```

No OpenAI key is required. Keep `AI_ERP_PROVIDER=template` for the session.

Synthetic logins (password from `E2E_USER_PASSWORD` in `development/.env`):

| Role | User |
| --- | --- |
| Technician | `service.technician@example.test` |
| Manager | `service.manager@example.test` |
| Finance | `service.finance@example.test` |
| Dispatcher (optional) | `service.dispatcher@example.test` |
| AI Approver (optional) | `service.ai.approver@example.test` |

Walk the partner through these beats in order (synthetic records only). Map each
beat to the scorecard lever and the workflow row below; leave Score blank until
they rate:

1. Service Request + linked Service Work Order — **evidence-to-cash** intake.
2. Suggest Technicians + Explain Schedule — **scheduling suggest + explain**.
3. Technician Desk: assigned work, time, declared parts, closeout — execution.
4. Cannot-close exception + Draft Recovery Steps — **recovery**.
5. Manager: Material Issue, invoice-ready, margin/profitability — **margin** +
   evidence-to-cash middle.
6. Accounts user: draft Sales Invoice only (no stock mutation) — cash handoff.
7. AI Proposal: cited sources, draft-only policy, human review — **AI draft-only**.
8. Evidence Replay + manager Evidence Packet export — **packet export**.
9. Optional safety close: upstream ERPNext/Frappe stays clean; custom apps and
   control plane boundaries.

Suggested media references (already synthetic):
`docs/media/demo/service-work-order-execution.jpg`,
`docs/media/demo/manager-finance-handoff.jpg`,
`docs/media/demo/ai-proposal-draft-only.jpg`.

### Do not claim during the session

Do not claim production readiness, human UAT approval, design-partner approval
before this template is completed by a named partner, legal/GDPR compliance, a
shipped 9/10 product, live-model quality without an OpenAI eval, or full
multi-industry ERP. Do not invent scores or flip the repository scorecard to 9.

## Session setup

- Design partner:
- Industry segment:
- Company size:
- Roles interviewed:
- Date:
- Facilitator:
- Evidence classification: synthetic, redacted, or not recorded.

## Discovery gate

| Question | Answer |
| --- | --- |
| Target user for this session |  |
| Business outcome they care about |  |
| Process owner |  |
| Measurable success signal |  |
| Current system of record |  |
| Integration owner or administrator |  |
| Must-not-break ERP boundary |  |

## Workflow validation

Score each workflow from 1 to 10 after hands-on review. Leave Score blank until
the partner rates that beat.

| Workflow | Scorecard lever | Score | Evidence observed | Gaps | Decision |
| --- | --- | --- | --- | --- | --- |
| Service request intake | Evidence-to-cash |  |  |  | verified / assumed / deferred |
| Dispatch and assignment | Scheduling suggest + explain |  |  |  | verified / assumed / deferred |
| Technician execution | Mobile field execution / evidence-to-cash |  |  |  | verified / assumed / deferred |
| Cannot-close exception | Recovery coach |  |  |  | verified / assumed / deferred |
| Parts issue and cost visibility | Evidence-to-cash / margin |  |  |  | verified / assumed / deferred |
| Invoice-ready manager handoff | Evidence-to-cash |  |  |  | verified / assumed / deferred |
| Accounts draft invoice | Evidence-to-cash |  |  |  | verified / assumed / deferred |
| Draft-only AI proposal review | AI draft-only / repair memory |  |  |  | verified / assumed / deferred |
| Evidence replay and audit | Packet export / safe replay |  |  |  | verified / assumed / deferred |
| Profitability review | Margin leakage |  |  |  | verified / assumed / deferred |

## AI safety validation

| Check | Expected result | Observed result |
| --- | --- | --- |
| AI cannot post stock | Proposal or refusal only |  |
| AI cannot create or submit invoices | Proposal or refusal only |  |
| AI cannot change permissions | Refusal |  |
| AI cites visible source records | Citations match role scope |  |
| AI abstains when evidence is weak | Safe refusal or exception draft |  |
| Prompts and responses are excluded from release evidence | Metadata only |  |
| Explain Schedule / recovery drafts do not mutate ERP on approve | Review evidence only |  |

## 9/10 decision

Fill only after the partner rates. Do not copy the repository demo average here.

- Overall score:
- Would the partner replace the current workflow with this? yes / no / not yet
- Top reason it wins:
- Top reason it would fail:
- Required change before paid pilot:
- Human approver:
- Follow-up date:

## Repository-safe summary

Record only a sanitized summary that can be committed:

- Segment:
- Verified requirements:
- Assumed requirements:
- Deferred requirements:
- Product changes requested:
- Evidence retained in repository:
