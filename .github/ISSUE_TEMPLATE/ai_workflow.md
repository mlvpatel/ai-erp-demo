---
name: AI workflow proposal
about: Propose a new AI-assisted ERP workflow or expansion of an existing one
title: "[AI workflow]: "
labels: ["ai-safety", "discovery", "triage"]
assignees: []
---

## Workflow goal

<!-- What job should AI help with, and for which ERP role? -->

## AI capability type

- [ ] Retrieval or summarization
- [ ] Classification or routing
- [ ] Draft document/proposal
- [ ] Exception explanation
- [ ] External communication draft
- [ ] Tool/action proposal

## Source ERP records

<!-- Which DocTypes or ERPNext records are source-of-truth inputs? -->

## Data leaving the Frappe site

Allowed fields:

- [ ]

Forbidden fields:

- [ ] Customer contact details
- [ ] Service addresses
- [ ] Attachment contents
- [ ] Credentials/secrets/private prompts
- [ ] Payroll/bank/tax/compliance data
- [ ] Stock valuation or accounting ledger lines
- [ ] Cross-tenant data

## Approval and audit

- Requesting role:
- Reviewing role:
- Audit record:
- Source citations or hashes:
- Prompt/model/version metadata:

## ERP safety boundary

- [ ] AI output is draft/proposal-only.
- [ ] AI cannot submit invoices, post stock, change payroll, alter permissions,
      make compliance decisions, or send external messages directly.
- [ ] Deterministic ERP code and authorized approval perform any final action.
- [ ] Retry/idempotency behavior is defined.

## Contract and tests

- [ ] Versioned contract needed.
- [ ] Negative test for unsupported action fields.
- [ ] Test proving approval has no unauthorized ERP side effect.
- [ ] Threat model and data-classification docs updated.

## Discovery evidence

<!-- Link interview notes, workflow evidence, screenshots with secrets removed,
or comparable workflows. -->
