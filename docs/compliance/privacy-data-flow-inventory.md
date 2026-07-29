# Privacy and data-flow inventory (synthetic demo)

Status: engineering inventory for the local synthetic demo. This is not a
Record of Processing Activities (RoPA), not a lawful-basis determination, and
not GDPR compliance evidence.

Default data mode: synthetic only (`config/pilot-readiness.json`). Real customer
or employee personal data must not enter the demo stack, Git, CI logs, or release
evidence.

## Systems in scope

| System | Role in demo | Holds durable business state? |
| --- | --- | --- |
| Frappe/ERPNext site (local Docker or Bench) | ERP system of record | Yes |
| `apps/ai_erp_service` | Field-service DocTypes and deterministic ERP actions | Yes (via site DB) |
| `apps/ai_erp_core` | AI Proposal ledger (draft-only, cited, reviewable) | Yes (via site DB) |
| `services/ai_control_plane` | Prompt shaping, redaction, provider call, audit metadata | No durable ERP state; request/response only |
| Template provider (default) | Deterministic draft text, no external network | No |
| OpenAI adapter (optional, gated) | External draft generation after minimization/redaction | Provider may process request content under its terms; demo must keep `store=false` |

## Data classes present in the synthetic demo

| Class | Examples in this repo | Classification (`docs/security/data-classification.md`) | May leave the ERP site toward an AI provider? |
| --- | --- | --- | --- |
| Synthetic customer/site identity | Seeded Customer, Contact, Address, Service Location | Public/internal design data when clearly fake | No contact/address fields in provider allow-list |
| Work execution | Service Request, Service Work Order, time/part rows, closeout notes, inspection fields | Internal design data when synthetic | Allow-listed subject/description/closeout/time/part facts only |
| Scheduling | Technician User, capability, suggestion feedback | Internal design data when synthetic | Scheduling explanation drafts use cited local context; no autonomous assign |
| Finance projection | Bill rates, part costs, margin helpers, draft Sales Invoice link | Business confidential if real; synthetic in demo | Not sent for unauthorized roles; not in closeout provider minimize path |
| Stock | Item, Warehouse, Stock Entry links from `issue_parts` | Business confidential if real | Warehouse identity stays out of provider minimize path |
| AI proposal metadata | Proposal type, draft content, citations, hashes, model/provider audit fields | Internal; treat as sensitive if real | Draft content is produced locally or by provider; raw prompts/responses stay out of Git |
| Secrets | API keys, DB passwords, session cookies | Secrets | Never |

## What AI may see (proposal-only boundary)

AI proposes. Deterministic ERP code and authorized humans post stock, invoices,
permissions, payroll, compliance records, and customer messages.

Proposal types in the demo:

- Service closeout draft
- Scheduling explanation draft
- Exception recovery draft
- Repair-memory draft

Provider minimize/redaction behavior (code paths):

- Closeout/repair-memory OpenAI paths strip tenant, user, work-order, and
  warehouse identifiers from the provider request and run
  `services/ai_control_plane/src/ai_erp_control_plane/safety.py` redaction
  (email, phone-shaped values, credential-shaped tokens).
- Template renderers redact contact/credential-shaped free text and neutralize
  instruction-like spans before writing `draft_content`.
- Retrieval is permission-scoped inside Frappe; missing or invisible evidence
  must abstain rather than invent sources.
- Audit records store redaction counts and hashes, not raw prompt/response
  bodies.

Authoritative detail: `docs/security/data-classification.md`,
`docs/security/ai-workflow-review.md`, ADR-0003, ADR-0004, ADR-0006.

## Retention intent (demo vs future pilot)

| Store | Demo intent | Pilot intent (owner must approve) |
| --- | --- | --- |
| Local site database | Disposable; reset via demo seed/reset helpers | Named retention schedule required |
| AI Proposal rows | Kept for demo review/replay; synthetic only | Retention, export, and erasure workflow required |
| Control-plane process memory | Ephemeral request handling | No durable PII store in this service |
| Provider (`store=false`) | No intentional provider retention by this app | DPA, transfer, and provider retention review required |
| Backups/logs | Local operator responsibility; keep out of Git | Approved RPO/RTO, log retention, and deletion drill |

## Related gates

- Gate checklist: `docs/compliance/eu-italy-gdpr-readiness.md`
- Counsel templates: `docs/compliance/dpa-template.md`,
  `docs/compliance/dpia-template.md`
- Human sign-off index: `docs/compliance/pilot-go-no-go-checklist.md`
- PII engineering notes: `docs/compliance/pii-handling-notes.md`
