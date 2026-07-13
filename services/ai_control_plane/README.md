# AI control plane

This is a stateless, draft-only service—not an ERP database client. It accepts
one versioned `service_closeout_summary` request, produces a cited draft, and
returns it to the calling Frappe site. It has no MariaDB, Redis, ERPNext, or
Frappe credentials.

The request/response contract is
[`contracts/openapi/ai-control-plane-v1.yaml`](../../contracts/openapi/ai-control-plane-v1.yaml).
The service accepts only a bearer credential supplied by the calling Frappe
site. In a deployed environment use a distinct secret and network policy for
each site; the returned `tenant_site` is an audit scope, not authorization by
itself.

## Providers

The default `template` renderer deterministically
formats submitted closeout fields and identifies itself as
`development-template` in every response. It is useful for running the entire
approval/audit path locally, but it is not represented as a production AI
model. There is deliberately no implicit cloud-model fallback.

The approved `openai` adapter uses the Responses API with strict structured
output and no tools. It removes tenant, user, record, source-hash, technician,
and warehouse identifiers before the request. Policy, citations, and provider
metadata are added locally and cannot be supplied by the model. The adapter
uses `store=false`, a bounded timeout/output, no retry, and fails closed as 503.

Production EU use requires an OpenAI project approved and contractually enabled
for European data residency and the corresponding abuse-monitoring control. Set
`AI_ERP_PROVIDER=openai`, keep `OPENAI_BASE_URL=https://eu.api.openai.com/v1`,
and inject `OPENAI_API_KEY` from the deployment secret manager. The only
allow-listed model is the pinned `gpt-5.4-mini-2026-03-17` snapshot. Do not put
keys in `.env` files committed to Git. Roll back instantly by selecting the
`template` provider; there is no implicit cloud-model fallback.

## Local checks

```sh
docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec ai-control-plane \
  python -m unittest discover -s tests -v
```
