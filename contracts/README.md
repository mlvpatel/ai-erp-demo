# Contracts

Public REST/OpenAPI schemas live in `openapi/`; asynchronous business-event
schemas live in `events/`. Contracts are versioned before implementation so
industry apps and external connectors stay independently deployable.

`catalog.json` is the source of truth for contract ownership, implementation
status, consumers, safety boundaries, and verification commands. Add every
public OpenAPI or business-event contract to the catalog before merging it.
The versioning and status workflow is documented in
`docs/workflows/contract-lifecycle.md` and checked by
`scripts/check-contract-lifecycle.py`.

`openapi/ai-control-plane-v1.yaml` is the first governed AI boundary. It only
permits a cited, draft-only service-closeout summary. Its response cannot carry
an ERP mutation instruction; new AI capabilities require a new versioned
contract and policy review.

`events/service-operations-v1.yaml` is the first business-event catalog. It is
contract-only until an approved connector emits events. Payloads are deliberately
minimal and do not contain customer contact details, addresses, attachment
contents, credentials, prompts, ledger lines, or mutation instructions.
