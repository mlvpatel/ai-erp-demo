# Contract lifecycle

Version public APIs and business events before implementing connectors,
industry-pack integrations, or cross-service AI workflows. Contracts are the
shared boundary between ERPNext/Frappe apps, the AI control plane, and future
external adapters.

## Statuses

### Planned

A planned contract is a design placeholder. Do not implement producers or
consumers until the owner area, safety boundary, and first consumer are known.

### Contract-only

A contract-only boundary has a published schema but no producer yet. Use this
for future connector/event surfaces where contributors need the safe payload
shape before implementation.

- Keep payloads minimal and synthetic-testable.
- Include tenant/site scope, actor/source information, and idempotency or
  correlation identifiers where relevant.
- Do not include customer contact details, service addresses, attachment
  contents, credentials, prompts, ledger lines, or mutation instructions.
- Add producer/consumer contract tests before an implementation emits or
  consumes the contract.

### Implemented

An implemented contract has at least one producer, at least one consumer or
contract test, and a verification command in `contracts/catalog.json`.

- OpenAPI contracts must keep strict schemas and explicit security schemes.
- Event contracts must keep strict envelopes and versioned event names.
- Contract changes that remove fields, loosen safety policy, or widen mutation
  authority require a new version.
- AI-facing contracts must keep `policy.decision = draft_only` and
  `policy.allowed_action = none` unless a future ADR explicitly changes the AI
  transaction boundary.

## Versioning rules

- Contract IDs end with `-vN`, where `N` is the major contract version.
- Contract filenames end with `-vN.yaml`.
- OpenAPI `info.version` uses SemVer and its major version matches the ID.
- Business-event catalog `version` is the major version string and every
  event type ends with `.vN`.
- Prefer additive, backward-compatible changes inside a major version.
- Use a new major version for breaking schema changes, changed authorization
  meaning, changed idempotency meaning, or expanded mutation authority.

## Required change set

When adding or changing a contract, update:

1. the contract file in `contracts/openapi/` or `contracts/events/`,
2. `contracts/catalog.json`,
3. `docs/workflows/contract-lifecycle.md` if lifecycle rules change,
4. producer and consumer tests in `tests/contract/`,
5. `docs/security/threat-model.md` when the trust boundary changes,
6. `docs/product/requirements-traceability.md` when public evidence changes,
7. `config/ai-workflow-registry.json` if the contract backs an AI workflow.

Never add unversioned webhooks, direct ERP mutation instructions, production
payload examples, customer exports, or secrets to a public contract.
