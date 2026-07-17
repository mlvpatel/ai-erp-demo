# AI workflow safety review

Use this checklist before adding or expanding any AI-assisted ERP workflow.
The default answer for consequential actions is still **no**: AI can draft,
summarize, classify, retrieve, explain, or propose; deterministic ERP code and
authorized people perform business mutations.

## Scope classification

Classify the workflow before design:

- [ ] Retrieval or summarization only.
- [ ] Classification or routing only.
- [ ] Draft document/proposal with human review.
- [ ] Exception explanation or decision support.
- [ ] Tool/action proposal that could later affect ERP state.
- [ ] External communication draft.

If the workflow can affect money, stock, payroll, permissions, compliance,
customer messaging, or external-system writes, it needs maintainer design review
and a contract/policy update before implementation.

## Required design answers

1. Which ERP record is the source of truth?
2. Which role may request the AI output?
3. Which role may review, approve, reject, or discard the output?
4. What exact fields leave the Frappe site?
5. Which fields are explicitly forbidden from leaving the site?
6. What source references or hashes prove the draft is grounded?
7. What model/provider, prompt version, and policy decision are recorded?
8. What happens on retry, timeout, duplicate response, or provider failure?
9. What test proves the AI output cannot directly mutate ERP state?
10. What audit record proves who requested and reviewed the output?
11. Which deterministic ERP record IDs, if any, prove the approved business
    action was later executed by ERP code instead of AI?

## Data boundary

Allowed by default:

- synthetic test data,
- record identifiers,
- service work-order subject and status,
- allow-listed closeout notes,
- typed time rows,
- typed part rows,
- source labels and source hashes.

Forbidden unless a future ADR and allow-list explicitly permit it:

- customer contact details,
- service addresses,
- attachment contents,
- credentials, API keys, cookies, or private prompts,
- payroll, bank, tax, credit, or regulated compliance data,
- stock valuation or accounting ledger lines,
- data from another tenant/site.

## Contract and test requirements

Every new AI workflow needs:

- a versioned OpenAPI or event contract if it crosses a service/integration
  boundary,
- strict request/response models with `extra = forbid` or equivalent,
- a negative test for unsupported action fields,
- a test proving returned policy is draft/proposal-only unless a later ADR
  explicitly authorizes a different pattern,
- a test proving review/approval does not create unauthorized ERP transactions,
- documentation updates in the workflow, threat model, and traceability docs.
- an audit evidence update when source hashes, review fields, or downstream ERP
  record links change.

## Rejection conditions

Do not implement the workflow if:

- it asks AI to submit invoices, post stock, change payroll, alter permissions,
  or make compliance decisions directly,
- it requires production customer exports or private attachments to reproduce,
- it bypasses Frappe permissions or tenant/site boundaries,
- it cannot produce a stable audit trail,
- retries could duplicate an ERP or external write,
- the workflow needs a new service, datastore, provider, or irreversible
  dependency and no ADR exists.

## Current approved AI workflow

The only approved MVP workflow is the service closeout summary:

- route: `POST /v1/proposals/service-closeout-summary`,
- proposal type: `service_closeout_summary`,
- policy: `draft_only`,
- allowed action: `none`,
- review side effect: records approval/rejection only.

The machine-readable data boundary for this workflow is
`config/ai-data-boundary.json`. The static quality gate runs
`scripts/check-ai-data-boundary.py` so the payload builder, strict models,
OpenAPI contract, tests, and safety docs stay aligned.

The approved AI workflow registry is `config/ai-workflow-registry.json`. The
static quality gate also runs `scripts/check-ai-workflow-registry.py` so future
AI routes, proposal types, data boundaries, docs, and tests are declared before
implementation.

The audit evidence contract is `config/audit-evidence.json`. The static quality
gate runs `scripts/check-audit-evidence.py` so AI Proposal ledger fields, source
hashes, reviewer metadata, and deterministic ERP record links remain reviewable.

## Approved production provider boundary

ADR-0006 approves OpenAI only for the existing service-closeout summary. The
adapter sends minimized operational facts without tenant, requester, record,
source-hash, technician, or warehouse identifiers. It uses the Responses API,
no tools, `store=false`, one strict `draft_content` field, a pinned model
snapshot, and bounded input/output. Policy and citations remain local.

This approval is technical, not permission to send real client data. An EU
OpenAI project with the required residency and retention controls, DPA/DPIA,
controller approval, and private live evaluation evidence are pre-production
gates. Missing configuration or any provider failure returns 503; the service
does not silently fall back.
