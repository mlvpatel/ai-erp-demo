# ADR-0010: Add a deterministic exception-recovery proposal type

- Status: Accepted
- Date: 2026-07-17
- Owners: AI ERP Demo

## Context

ADR-0009 established the registration pattern for additional governed proposal
types: an explicit data-boundary manifest, a registry entry, a versioned
contract route, and a deterministic renderer when no hosted provider is
approved. Managers who own a Cannot Close work order still assemble recovery
steps by hand from the exception reason, inspection outcome, declared parts,
and prior work at the same asset or location.

## Decision

Register a third proposal type, `exception_recovery`, under the same rules:

- The control plane exposes `POST /v1/proposals/exception-recovery`
  (contract 1.4.0) and always renders deterministically from supplied facts.
  Reason categories map to fixed recovery checklists; no hosted model is
  involved, and extending ADR-0006 here would require a new ADR.
- The request carries the open closure exception, the work-order execution
  facts, and permission-scoped related work history. Customer and location
  identifiers stay out of the contract.
- Weak evidence abstains explicitly: an uncategorized reason with no prior
  history produces a stated abstention instead of invented recovery steps.
- The proposal is draft-only with allowed action `none`. The manager owns the
  exception, the recovery action, and closure; approval records review
  evidence and cannot change work-order state.

## Consequences

- The ledger allowlist grows to three draft-only types sharing one lock,
  dedupe, and rate-limit path.
- The data-boundary checker validates each registered manifest with the same
  function, so a fourth workflow needs registration, not new checker code.
