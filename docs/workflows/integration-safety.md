# Integration safety

External integrations must not become a shortcut around ERP permissions,
idempotency, audit, or contract versioning. The MVP keeps
`apps/ai_erp_connectors/` reserved and publishes only contract-only business
event shapes for future adapters.

## MVP rules

- Do not add connector implementation code until a concrete workflow has a
  versioned OpenAPI or business-event contract and contract tests.
- Business events are notifications. They do not authorize ERP mutations.
- Event payloads carry identifiers and workflow facts only; they must not carry
  customer contact details, service addresses, attachment contents,
  credentials, private prompts, ledger lines, or mutation instructions.
- Future adapter writes must be idempotent and store external identifiers plus
  sync status on ERP or connector-owned records.
- Future webhook or sync failures must become reviewable ERP records, not
  hidden logs only.
- Provider SDKs, generic sync frameworks, and unversioned webhooks need a
  future ADR before implementation.

## Required change set for a connector

Before any connector app code is added:

1. Add or update a versioned contract under `contracts/`.
2. Add the contract to `contracts/catalog.json` with owner, producer, consumer,
   safety boundary, tests, and verification.
3. Add producer/consumer contract tests.
4. Update the threat model if a trust boundary changes.
5. Document idempotency, authorization, audit evidence, and failure surfacing.

The machine-readable integration safety contract is
`config/integration-safety.json`. The static quality gate runs
`scripts/check-integration-safety.py` so connector reservation state, event
contracts, catalog safety boundaries, tests, and docs stay aligned.
