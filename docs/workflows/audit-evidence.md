# Audit evidence

An audit reviewer must be able to trace an AI-supported transaction from the
source ERP record to the AI Proposal and back to deterministic ERP records.
The MVP keeps this evidence inside Frappe/ERPNext records; the AI control plane
does not become the system of record.

## Evidence chain

1. The Service Work Order is the source ERP record for the MVP workflow.
2. The AI closeout request records allow-listed source references and source
   hashes before calling the control plane.
3. AI Proposal is the AI evidence ledger for the MVP. It records the proposal
   type, draft-only policy result, reference record, draft content,
   `input_context_hash`, `output_hash`, `control_plane_request_id`,
   requested_by, generated_at, model provider, model name, prompt version, and
   cited sources.
4. AI Proposal Source rows record source_doctype, source_name, source_field,
   and content_hash for each cited input.
5. Human review records reviewed_by, reviewed_at, and reviewer_note on the AI
   Proposal. Approval or rejection does not create ERP transactions.
6. Deterministic ERP actions store their resulting record identifiers on the
   source record. Stock Entry identifiers are stored on Service Work Order part
   rows. Sales Invoice identifiers are stored on the Service Work Order.

## Append-only ledger

AI Proposal rows cannot be deleted. No role in the doctype carries a delete
grant, and the controller's `on_trash` refuses deletion outright, so a
proposal and its Source child rows stay in place once written. The static
gate checks both: it fails if any permission row regains a delete grant or if
the `on_trash` guard disappears from the controller. The guard covers
`frappe.delete_doc`; a raw SQL delete bypasses document hooks, and no code
path in the custom apps issues one against this table.

## Review expectations

Every future AI workflow must answer:

- Which ERP record is the source of truth?
- Which source fields are included, and which content hash proves each one?
- Which policy decision proves the model can only draft or propose?
- Which user requested the output?
- Which model provider, model name, and prompt version produced it?
- Which user reviewed it, when, and with what note?
- Which deterministic ERP record IDs were created afterward, if any?

If an answer cannot be stored on an ERP record or versioned contract, do not
implement the workflow yet.

## Static guardrail

The machine-readable audit evidence contract is
`config/audit-evidence.json`. The static quality gate runs
`scripts/check-audit-evidence.py` to keep DocType fields, source-code anchors,
tests, and safety documentation aligned.
