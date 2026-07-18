# ADR-0011: Add a deterministic repair-memory proposal type

- Status: Accepted
- Date: 2026-07-17
- Owners: AI ERP Demo

## Context

Technicians and managers repeat diagnostics that earlier visits already
answered. The permission-scoped history retrieval from the closeout workflow
already returns completed work at the same asset or location with citations,
and ADR-0009/ADR-0010 established the registration pattern for deterministic
proposal types.

## Decision

Register a fourth proposal type, `repair_memory`, under the same rules:

- The control plane exposes `POST /v1/proposals/repair-memory`
  (contract 1.5.0) and always renders deterministically. The draft only
  reorganizes supplied cited facts: prior closeout notes become the likely-fix
  section, parts used across prior visits become the parts-likely-required
  list with occurrence counts, and failed or follow-up inspection outcomes
  become the missing-diagnostic warning. Nothing outside the supplied history
  can appear, so invented parts are structurally impossible.
- History entries come from the same role-scoped retrieval as the closeout
  workflow, extended with each entry's declared parts. A requester without
  visible history receives an explicit abstention draft.
- The proposal is draft-only with allowed action `none`; approval records
  review evidence and cannot change the work order, stock, or billing.

## Consequences

- The ledger allowlist grows to four draft-only types on one shared request
  path.
- Structured, provenance-based retrieval remains the foundation; a vector
  store or embedding model still requires its own ADR and evaluation.
