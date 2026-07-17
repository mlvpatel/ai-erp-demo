# Field Service 9/10 Target

This document defines the next build target after the zero-cost local demo. It
does not claim the current system is a 9/10 product. It defines the evidence,
workflow depth, and safety gates required to become a high-quality product in
one narrow category:

> Governed AI-native field-service ERP for small and midsize maintenance,
> installation, and repair firms with 10 to 100 technicians.

The product should win by making the path from field evidence to invoice safer,
faster, and more auditable than a spreadsheet-driven service desk or a generic
ERP chatbot.

## Target user

- Primary user: field-service operations manager.
- Secondary users: dispatcher, technician, accounts user, AI reviewer, and owner
  or finance lead.
- Buyer signal: the team loses money or trust because work orders close with
  missing evidence, duplicated parts, unclear margin, delayed invoices, or weak
  handoff between operations and finance.

## Business outcome

Turn a service request into assigned work, verified execution, margin-aware
closeout, and one draft invoice without losing source evidence or crossing ERP
authorization boundaries.

Success is measured by:

- At least 95 percent of work orders reaching invoice-ready state with required
  evidence or an owned exception.
- Zero autonomous AI posting to stock, accounting, payroll, permissions, or
  compliance records.
- No duplicate stock issue, invoice draft, or AI proposal under retry or
  concurrency tests.
- Manager and accounts users can replay the evidence chain without inspecting
  raw logs or prompts.
- Design partners rate the evidence-to-cash workflow at 9/10 or better after
  hands-on validation.

## Flagship capability

The flagship capability is a verifiable evidence-to-cash ledger:

1. A technician records time, parts requested or used, closeout notes, and
   permitted evidence.
2. The system validates missing data, permissions, exceptions, idempotency, and
   tenant scope before a manager can mark the work invoice-ready.
3. AI may draft a cited closeout or exception proposal, but cannot post stock,
   create invoices, send customer messages, change permissions, or approve its
   own output.
4. Finance creates exactly one linked draft invoice through standard ERPNext
   permissions.
5. Managers can replay the chain from request to work order, stock issue,
   proposal, review, margin projection, and invoice draft.

## Differentiators

| Differentiator | Why it matters | Current state | Target gate |
| --- | --- | --- | --- |
| Verifiable evidence-to-cash ledger | Turns operational evidence into a finance handoff without losing auditability. | Partly implemented in the local demo. | Full replayable ledger with role-scoped UI and exportable release evidence. |
| Cannot-close recovery coach | Keeps unresolved work visible with a named human owner instead of silently closing weak jobs. | Implemented as deterministic exception ownership and escalation. | AI may draft recovery suggestions, but a manager owns every action. |
| Margin leakage guardian | Shows where discounts, part cost, missing billable time, or repeated visits reduce margin. | Basic projected margin exists. | Finance-safe profitability report with permission-scoped search and alerts. |
| Provenance-based repair memory | Reuses previous fixes only when source work orders and citations are visible to the role. | AI proposal citations exist for closeout. | Permission-scoped retrieval with abstention when evidence is weak. |
| Safe agent replay | Lets reviewers see what an AI agent would do without giving it posting authority. | Draft-only AI proposals exist. | Replay harness covers scheduling, closeout, exception, and invoice-handoff proposals. |
| Bounded scheduling optimizer | Suggests assignments using skills, location, SLA, workload, and parts readiness. | Dispatcher assignment is manual. | Optimizer proposes only; dispatcher approves or edits. |
| Mobile field execution | Makes technician work fast on desktop and mobile without exposing finance data. | Browser journeys exist. | Mobile-first workflows, attachments, keyboard access, and offline-safe drafts. |

## AI decision boundary

AI is allowed to:

- Summarize source records with citations.
- Detect missing evidence, likely closure blockers, and margin leakage signals.
- Draft recovery, closeout, scheduling, and invoice-handoff proposals.
- Explain why a proposal was refused or why it abstained.

AI is prohibited from:

- Posting accounting, tax, stock, payroll, compliance, or permission changes.
- Submitting invoices, stock entries, material requests, delivery notes, or work
  orders.
- Sending customer communications.
- Approving, reviewing, or hiding its own proposals.
- Using prompts, raw provider responses, credentials, or customer data as
  release evidence.

## Release phases

1. Phase 1: define the 9/10 category, target scorecard, design-partner template,
   and static quality gate.
2. Phase 2: deepen field-service foundations: assets, SLAs, warranties,
   inspections, preventive work, attachments, mobile ergonomics, and manager
   reporting.
3. Phase 3: upgrade the governed AI kernel: real provider path, permission-scoped
   retrieval, redaction, evals, spend controls, and abstention.
4. Phase 4: complete the evidence-to-cash ledger across UI, audit, exports,
   profitability, idempotent finance handoff, and replay.
5. Phase 5: add bounded scheduling and exception agents that propose only and
   include deterministic validation.
6. Phase 6: add repair memory and margin intelligence backed by citations and
   role-scoped retrieval.
7. Phase 7: prove production-pilot readiness with deployment, recovery,
   capacity, support, UAT, legal, and go/no-go evidence.

## Claim boundary

Until every target gate has evidence, describe the repository as:

- A private zero-cost local AI ERP demo.
- A governed field-service foundation.
- A roadmap and scorecard for a differentiated 9/10 field-service ERP.

Do not describe it as:

- Production ready.
- Human UAT approved.
- Legal or GDPR compliant.
- A full multi-industry ERP.
- A 9/10 product.
