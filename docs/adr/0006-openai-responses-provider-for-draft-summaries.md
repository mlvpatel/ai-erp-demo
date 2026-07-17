# ADR-0006: Use a minimized OpenAI Responses adapter for draft summaries

- Status: Accepted
- Date: 2026-07-14
- Owners: AI ERP Demo

## Context

The deterministic renderer proves the governed workflow but is not a production
AI provider. A real provider changes the data trust boundary and must preserve
ADR-0003 and ADR-0004: AI creates proposals only, while ERP validation and
authorized people control every mutation.

## Decision

Add one allow-listed OpenAI Responses API adapter for
`service_closeout_summary`. Use the pinned `gpt-5.4-mini-2026-03-17` snapshot,
strict JSON-schema output, `store=false`, no tools, a bounded output and timeout,
and no automatic retry. Pinning plus synthetic evaluations makes prompt/model
changes explicit.

Before the model call, remove tenant site, requester, work-order ID, technician,
warehouse, source record, and hash identifiers. The model may return only
`draft_content`. The control plane constructs the fixed `draft_only/none`
policy, exact citations, request ID, and model metadata locally. Missing keys,
unapproved origins/models, timeouts, refusals, malformed output, and HTTP errors
all fail closed without exposing provider details.

EU production uses `https://eu.api.openai.com/v1` only after the OpenAI project
has European data residency plus the required retention/abuse-monitoring terms.
Until the controller completes its DPA/DPIA and approves real pilot data, only
synthetic data may be sent. Keys come from the deployment secret manager and
the service receives no ERP database credentials.

## Consequences

- The proposal contract and ERP mutation boundary do not change.
- Provider cost and latency are bounded but remain external dependencies.
- Free-text operational notes leave the ERP trust boundary; data minimization,
  legal approval, retention settings, and incident procedures are mandatory.
- Rollback is configuration-only: select `template`; never silently fall back
  from OpenAI because that would hide production degradation.

## Alternatives considered

- Model calls inside Frappe: rejected because they blur provider governance and
  expose the transactional runtime to an external dependency.
- Model-generated citations or policy: rejected because untrusted output cannot
  authorize itself or alter audit evidence.
- Generic chat/tools: rejected because this workflow needs neither retrieval nor
  actions and must not gain an ERP write path.
