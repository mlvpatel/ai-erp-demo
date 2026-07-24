# Design-partner facilitator runbook

Step-by-step guide for running a **hands-on design-partner validation session**
on the local synthetic demo. No OpenAI key is required: the default
`AI_ERP_PROVIDER=template` path is deterministic and sufficient for governance
and workflow review.

This runbook prepares the session. It does **not** fill partner scores, claim
human UAT approval, production readiness, legal/GDPR compliance, or a 9/10
product rating.

Record scores only in
[`docs/discovery/design-partner-validation-template.md`](../discovery/design-partner-validation-template.md)
during or after a real partner session. Leave score cells blank until then.

## Do not claim (say out loud if asked)

Do **not** say or write that the product is:

- production ready
- human UAT approved
- design-partner approved (until a named partner completes the template)
- legally approved or GDPR compliant
- a shipped 9/10 field-service ERP
- multi-industry ERP beyond the field-service synthetic vertical
- powered by a live hosted model for this session (template provider only)

Do **not**:

- invent partner scores or copy demo averages into blank score cells
- flip `config/field-service-9-scorecard.json` to 9.x based on a rehearsal
- post stock, submit invoices, change permissions, or send customer messages via AI
- show `development/.env`, passwords, tokens, raw prompts, or provider responses
- use real customer, employee, or production data

Demo claim for the room: **private zero-cost local synthetic service-operations
demo with draft-only AI proposals**.

## Scorecard levers this walkthrough covers

| Lever (scorecard feature) | Partner sees | Template workflow rows |
| --- | --- | --- |
| Evidence-to-cash ledger | Request → work → parts → invoice-ready → draft invoice → replay | intake, execution, parts, invoice-ready, accounts draft, evidence replay |
| AI draft-only | Closeout / repair-memory proposals; approval does not post ERP | Draft-only AI proposal review; AI safety table |
| Scheduling suggest + explain | Suggest Technicians; Explain Schedule draft | Dispatch and assignment |
| Margin leakage | Profitability / margin risk on manager/finance views | Profitability review; parts and cost visibility |
| Cannot-close recovery | Exception + Draft Recovery Steps | Cannot-close exception |
| Packet export | Manager Evidence Packet JSON (sanitized) | Evidence replay and audit |
| Safe agent replay / AI safety | Beat J live safety table + draft-only approve | Entire AI safety validation table |

Source of truth for lever definitions:
`config/field-service-9-scorecard.json` and
`docs/product/field-service-9-target.md`.

## 0. Day-before checklist (facilitator alone)

```sh
cp development/.env.example development/.env   # only if missing
# Confirm AI_ERP_PROVIDER=template (default). Leave OPENAI_API_KEY empty.
scripts/dev.sh check-local-env
scripts/dev.sh demo-info
```

Optional hosts entry if the browser cannot resolve the site:

```text
127.0.0.1 ai-erp.localhost
```

## 1. Start the stack

Terminal A:

```sh
scripts/dev.sh up
scripts/dev.sh bootstrap   # first run or after pin/app changes
```

Terminal B (keep running):

```sh
scripts/dev.sh bench-start
```

Desk URL (from `scripts/dev.sh demo-info`):

```text
http://ai-erp.localhost:8000/app
```

Administrator password: read `ADMIN_PASSWORD` from `development/.env`. Never
print, commit, or share it in chat, screenshots, or the validation template.

## 2. Seed and prove the demo path

```sh
scripts/dev.sh seed-demo
scripts/dev.sh demo-check
```

`seed-demo` is idempotent. It creates synthetic masters, users, a Service
Request, a Scheduled Service Work Order, and initial stock. It does **not**
issue parts, create a Sales Invoice, approve an AI Proposal, or mutate ERP
state through AI.

If `demo-check` fails, fix blockers before the partner arrives. Do not run the
session on a broken seed.

## 3. Login roles (synthetic only)

Passwords for seeded users come from `E2E_USER_PASSWORD` in
`development/.env` (set by seed). Do not record passwords in the validation
template.

| Role in room | Login | Primary job this session |
| --- | --- | --- |
| Technician | `service.technician@example.test` | Assigned work, time, parts declare, closeout |
| Manager | `service.manager@example.test` | Suggest/assign, stock issue, invoice-ready, recovery, replay, packet |
| Finance | `service.finance@example.test` | Draft Sales Invoice only (Accounts User) |
| Dispatcher (optional) | `service.dispatcher@example.test` | Suggest Technicians / Explain Schedule |
| AI Approver (optional) | `service.ai.approver@example.test` | Review AI Proposal without posting ERP |

Always log out between role switches. Prefer separate browser profiles if the
partner will drive the keyboard.

## 4. Screen-by-screen walkthrough

Keep each beat short. After each beat, pause for partner reaction, then note
evidence / gaps in the matching template rows (scores stay blank until they
rate).

### Beat A: Intake (evidence-to-cash start)

1. Open **Service Request** → synthetic subject such as
   `AI ERP Demo Pump Inspection`.
2. Open the linked **Service Work Order**.
3. Point out customer, location/asset fields, status, and assignment fields.

**Ask:** Does this match how work enters their process today?

**Record in template:** Workflow → Service request intake.

### Beat B: Scheduling suggest + explain

1. As manager or dispatcher, on a draft work order with **Scheduled Start** and
   **Scheduled End** set (required before suggestions), use
   **Suggest Technicians**.
2. Show ranked candidates and exclusion reasons. Emphasize: suggestions do
   **not** assign anyone until a human saves the assignment.
3. Use **Explain Schedule** to create a draft-only AI Proposal that explains
   the ranking. Approval of that proposal cannot assign a technician.

**Ask:** Would dispatchers trust ranked suggestions with visible exclusion
reasons?

**Record in template:** Workflow → Dispatch and assignment; AI safety rows as
relevant.

### Beat C: Technician execution (mobile-aware)

1. Log in as `service.technician@example.test`.
2. Open assigned work only; show that finance/margin fields are not exposed.
3. Walk time entries, declared parts, closeout notes / evidence path.
4. Optional: narrow the browser to a phone width to show mobile field CSS.

**Ask:** What is missing for a real visit? What must never be visible to techs?

**Record in template:** Workflow → Technician execution; Parts issue and cost
visibility (tech side).

### Beat D: Cannot-close recovery

1. As technician or manager, show (or create on a disposable synthetic order) a
   **Cannot Close** / closure exception path with an owner and reason.
2. As manager, use **Draft Recovery Steps**. Show the draft is a checklist /
   proposal only.
3. State clearly: AI cannot close the work order or clear the exception.

**Ask:** Who owns recovery today? Would a draft checklist help or distract?

**Record in template:** Workflow → Cannot-close exception; AI safety table.

### Beat E: Manager stock + invoice-ready (evidence-to-cash middle)

1. Log in as `service.manager@example.test`.
2. Confirm **Labor Billing Item** / hourly rate and **Part Bill Rate** on each
   declared part (finance draft will refuse empty rates; missing rates also
   show up as margin-risk categories).
3. Issue declared parts (Material Issue / stock evidence linked on part rows).
4. Close / mark **Invoice Ready** when gates pass.
5. Retry the same action once to show idempotency (no duplicate stock).

**Ask:** Who posts stock in their org? What should block invoice-ready?

**Record in template:** Workflow → Parts issue and cost visibility; Invoice-ready
manager handoff.

### Beat F: Margin leakage

1. Still as manager (or accounts), open **Service Profitability** / projected
   margin and margin-risk categories on the work order or report.
2. Emphasize: classification is deterministic; missing cost becomes an unknown
   category, not an invented margin. Technicians must not see finance fields.

**Ask:** Which leakage categories matter most before billing?

**Record in template:** Workflow → Profitability review.

### Beat G: Finance draft invoice

1. Log out; log in as `service.finance@example.test`.
2. Create the linked **draft Sales Invoice** from the work order action.
3. Show draft-only: no stock update, no submit/post in the demo claim.
4. Retry once to show a single linked draft (idempotent).

**Ask:** Is Accounts User the right role mapping for their finance team?

**Record in template:** Workflow → Accounts draft invoice.

### Beat H: AI draft-only closeout / repair memory

1. As technician or manager, request **Draft Closeout Summary** on a closeout-
   submitted order and/or **Draft Repair Memory** on a **Scheduled** or
   **In Progress** order (repair memory is not available after closeout).
2. Open **AI Proposal**: citations, source hashes, model/prompt metadata,
   draft content, human review fields.
3. Review (approve or reject) as AI Approver / manager with approver role.
4. State: approval records review evidence only; it does **not** post invoices,
   stock, status, payroll, permissions, compliance, or emails.
5. Note that this session uses the **template** provider, not live OpenAI.

**Ask:** Is the citation + abstention behavior useful enough without a live
model?

**Record in template:** Workflow → Draft-only AI proposal review; entire AI
safety table.

### Beat I: Evidence replay + packet export

1. As manager on the Service Work Order, open **Evidence Replay**.
2. Walk completeness, missing evidence, exceptions, parts, AI proposal status,
   and finance handoff (manager/finance only).
3. Use **Evidence Packet** to export sanitized JSON. Confirm it has identifiers,
   hashes, statuses, and links: **not** draft text, prompts, or attachments.
4. Optional media references (already synthetic):
   `docs/media/demo/service-work-order-execution.jpg`,
   `docs/media/demo/manager-finance-handoff.jpg`,
   `docs/media/demo/ai-proposal-draft-only.jpg`.

**Ask:** Would ops/finance use replay + packet instead of digging through
emails?

**Record in template:** Workflow → Evidence replay and audit.

### Beat J: Safety close (demonstrable, ~5 minutes)

Do **not** end on a verbal reminder only. Walk the AI safety validation table
live so a partner can honestly rate Safety at 9/10 when the checks pass.

1. **Proposal-only proof (Desk).** On an approved AI Proposal from Beat H,
   show work-order status, stock links, and Sales Invoice are unchanged by
   Approve. Repeat the line: approval is review evidence only.
2. **Abstention / refusal.** If template provider produced a refusal or weak-
   evidence path earlier, reopen it; otherwise open a disposable WO without
   closeout notes and show Draft Closeout is blocked or abstains rather than
   inventing facts.
3. **Role scope.** As technician, confirm Evidence Replay hides Finance and
   that margin / profitability actions are denied. As manager, confirm the
   same packet export has hashes and links: **no** draft text or prompts.
4. **Explain Schedule / recovery non-mutation.** Point at Beat B / D: Approve
   did not assign a technician and did not clear the exception.
5. **Automated evidence (optional, 30s).** If the partner wants engineering
   proof, mention the local gates already covering this session path:
   `scripts/dev.sh e2e-test` (AI approve does not post ERP) and
   `tests/contract/test_replay_harness.py` (four draft-only fixtures, no
   money/stock/permission side effects). Do not run a long gate mid-session
   unless asked.
6. **Architecture boundary (15s).** Upstream ERPNext/Frappe stays clean;
   custom behavior is in `apps/`; AI orchestration is in
   `services/ai_control_plane/`; distribution / manufacturing packs are
   configured demos only.
7. **Claim hygiene (15s).** Current scorecard demo average is below 9 and is
   **not** a partner rating. Fill the 9/10 decision only after the partner
   scores; leave blank cells blank.

**Ask:** Which safety check would block a paid pilot if it failed tomorrow?

**Record in template:** Entire AI safety validation table (Observed result);
Discovery gate answers; 9/10 decision section only after the partner rates;
repository-safe summary without PII.

## 5. Where to write scores

Open a **copy** of
`docs/discovery/design-partner-validation-template.md` (or fill the tracked
file only with sanitized, partner-approved notes):

1. **Session setup**: partner name class, segment, roles, date, facilitator.
2. **Discovery gate**: outcome and system-of-record answers.
3. **Workflow validation**: fill Score / Evidence / Gaps / Decision **only
   after** hands-on review. Leave blank if the partner deferred a beat.
4. **AI safety validation**: Observed result column from what they saw.
5. **9/10 decision**: overall score and replace-workflow answer from the
   partner, not the facilitator.
6. **Repository-safe summary**: sanitized only; no credentials, prompts, or
   customer data.

Never commit raw partner PII, credentials, or screenshots that leak local
passwords.

## 6. After the session

Facilitator-only:

- Keep blank cells blank if the partner did not rate that row.
- Do not update `current_demo_average_score` in the scorecard from facilitator
  opinion alone.
- File product changes as backlog items; do not claim pilot approval.
- Live OpenAI evaluation remains a separate private path:
  `docs/runbooks/openai-live-evaluation.md` (deferred without a key).

## Related docs

- Local stack detail: [`local-demo.md`](local-demo.md)
- Recording / screenshot script: [`demo-script.md`](demo-script.md)
- Internal facilitator dry-run notes (not partner scores):
  [`design-partner-dry-run-notes.md`](design-partner-dry-run-notes.md)
- Synthetic UAT rehearsal (engineering, not partner approval):
  [`service-operations-synthetic-uat.md`](service-operations-synthetic-uat.md)
- Interview prompts: [`../discovery/service-operations-interview-guide.md`](../discovery/service-operations-interview-guide.md)
- Scorecard: `config/field-service-9-scorecard.json`
