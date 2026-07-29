# Data processing agreement template (for counsel)

Status: **template only**. Not executed. Not a signed DPA. Not evidence that a
processor relationship is lawful.

Use this outline with qualified counsel when a production or real-data pilot
would engage subprocessors (for example a model provider). Do not fill signed
party names, contract IDs, or personal data into this repository. Record
completed agreements in a private evidence system and leave only a reference on
`docs/compliance/service-operations-pilot-evidence-template.md`.

## How to use

1. Counsel adapts this outline to the controller's jurisdiction and the
   provider's current standard DPA.
2. Controller and processor sign outside Git.
3. Record decision date and private evidence reference on the pilot evidence
   template and go/no-go checklist.
4. Keep `config/pilot-readiness.json` gates `dpa-dpia-transfer-review` and
   related legal rows at `pending` until that private evidence exists.

## Parties (complete privately)

- Controller legal name:
- Controller contact for notices:
- Processor / provider legal name:
- Subprocessors known at signature (attach current list privately):
- Effective date:
- Governing law / venue (counsel):

## Processing description (draft for counsel review)

- Nature of processing: generation of draft text for human review inside an ERP
  workflow; no autonomous posting of stock, invoices, payroll, permissions,
  compliance records, or customer messages by the model provider path in this
  repository's design.
- Purpose: assist authorized users with closeout, scheduling explanation,
  exception recovery, and repair-memory drafts for field-service operations.
- Categories of data subjects (if real data is ever used): customers, site
  contacts, technicians, managers, finance users as present in the controller's
  ERP tenant.
- Categories of personal data: only fields the controller allow-lists after
  minimization; contact and credential-shaped values are intended to be
  redacted before provider calls in this codebase. Counsel must verify the
  live configuration.
- Special categories: not in MVP scope; do not send without a separate legal
  decision.
- Duration: request lifetime plus any provider-side retention the DPA permits;
  this repository's OpenAI path is designed with `store=false`.

## Controller instructions expected from this product design

- Process only instructions from the authenticated control-plane request path.
- Do not use demo/pilot inputs to train models unless the signed DPA expressly
  allows it.
- Return outputs to the control plane for local proposal recording; the ERP
  remains the system of record for business state.
- Support deletion/return assistance consistent with the signed DPA when the
  controller exercises rights.

## Security and audit (engineering baseline; counsel must approve)

- Encryption in transit to the provider endpoint.
- Secrets only from an approved secret store (never Git).
- Redaction/minimization before provider call where implemented.
- Audit metadata without raw prompt/response bodies in Git or public CI.

## International transfers

Counsel must document transfer mechanism (for example SCCs), destination
regions, and any Italy/EU-specific constraints. Hosting target noted in
`docs/compliance/eu-italy-gdpr-readiness.md` is AWS `eu-central-1` for a future
pilot; that note is not a transfer approval.

## Sign-off (private; do not commit signatures)

| Role | Name | Date | Private evidence reference | Decision |
| --- | --- | --- | --- | --- |
| Controller counsel |  |  |  |  |
| Controller accountable owner |  |  |  |  |
| Processor countersignature |  |  |  |  |

Decision values when complete: approved / rejected / deferred. Leave rows blank
in Git.
