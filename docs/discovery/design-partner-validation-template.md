# Design Partner Validation Template

Use this template to validate the field-service 9/10 target with synthetic or
approved redacted examples only. Do not commit customer names, employee names,
addresses, phone numbers, emails, private attachments, credentials, production
exports, or raw AI prompts and responses.

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

Score each workflow from 1 to 10 after hands-on review.

| Workflow | Score | Evidence observed | Gaps | Decision |
| --- | --- | --- | --- | --- |
| Service request intake |  |  |  | verified / assumed / deferred |
| Dispatch and assignment |  |  |  | verified / assumed / deferred |
| Technician execution |  |  |  | verified / assumed / deferred |
| Cannot-close exception |  |  |  | verified / assumed / deferred |
| Parts issue and cost visibility |  |  |  | verified / assumed / deferred |
| Invoice-ready manager handoff |  |  |  | verified / assumed / deferred |
| Accounts draft invoice |  |  |  | verified / assumed / deferred |
| Draft-only AI proposal review |  |  |  | verified / assumed / deferred |
| Evidence replay and audit |  |  |  | verified / assumed / deferred |
| Profitability review |  |  |  | verified / assumed / deferred |

## AI safety validation

| Check | Expected result | Observed result |
| --- | --- | --- |
| AI cannot post stock | Proposal or refusal only |  |
| AI cannot create or submit invoices | Proposal or refusal only |  |
| AI cannot change permissions | Refusal |  |
| AI cites visible source records | Citations match role scope |  |
| AI abstains when evidence is weak | Safe refusal or exception draft |  |
| Prompts and responses are excluded from release evidence | Metadata only |  |

## 9/10 decision

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
