# ADR-0009: Add a deterministic scheduling-explanation proposal type

- Status: Accepted
- Date: 2026-07-17
- Owners: AI ERP Demo

## Context

The first governed AI workflow, `service_closeout_summary`, is protected by a
single-workflow pin: the data-boundary checker rejects any other workflow, the
AI Proposal ledger accepts one proposal type, and ADR-0006 scopes the hosted
provider to closeout summaries. The scheduling optimizer now produces ranked,
deterministic technician suggestions, and dispatchers need a reviewable
explanation of those rankings that lives in the same audited proposal ledger.

## Decision

Add a second registered proposal type, `scheduling_explanation`, with a
narrower trust profile than the closeout summary:

- The control plane exposes `POST /v1/proposals/scheduling-explanation`
  (contract 1.3.0). The route always renders deterministically from the
  supplied ranking facts. It never calls a hosted model provider; extending
  ADR-0006 to scheduling would require a new ADR and evaluation evidence.
- The request carries only ranking facts: a minimal work-order summary,
  candidate scores, workloads, familiarity counts, reason codes, and exclusion
  reasons. Customer and location identifiers stay out of the contract.
- The proposal remains draft-only with allowed action `none`. Approving the
  explanation records review evidence and cannot change an assignment; the
  dispatcher assigns through the permission-checked form save.
- The single-workflow pin becomes an explicit registration: the data-boundary
  manifest lists additional workflows, and the checker validates each
  registered workflow's request model and contract route. Unregistered
  workflows keep failing the gate.

## Consequences

- The AI Proposal ledger allowlist grows to two types, both draft-only, and
  the request path shares the same lock, dedupe, and rate-limit controls.
- The registry, contract catalog, and lifecycle checks version the new route
  as an additive minor contract change.
- Refusal semantics stay deterministic: a missing schedule window aborts
  before any proposal exists, and zero familiarity evidence is stated in the
  draft instead of being dressed up as confidence.
