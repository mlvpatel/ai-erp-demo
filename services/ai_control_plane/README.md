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
Each render is limited to one provider call, zero automatic retries, 32,000
input bytes, 2,000 output tokens, and a provider timeout of at most 30 seconds.
These limits bound per-request spend; production also requires a provider
project hard budget and alert.

Production EU use requires an OpenAI project approved and contractually enabled
for European data residency and the corresponding abuse-monitoring control. Set
`AI_ERP_PROVIDER=openai`, keep `OPENAI_BASE_URL=https://eu.api.openai.com/v1`,
and inject `OPENAI_API_KEY` from the deployment secret manager. The only
allow-listed model is the pinned `gpt-5.4-mini-2026-03-17` snapshot. Do not put
keys in `.env` files committed to Git. Roll back instantly by selecting the
`template` provider; there is no implicit cloud-model fallback.

The credentialed synthetic provider check is intentionally excluded from
public CI. Operators can run it only through the secret-store and synthetic-data
gates in [`docs/runbooks/openai-live-evaluation.md`](../../docs/runbooks/openai-live-evaluation.md).

## Local checks

```sh
docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec ai-control-plane \
  python -m unittest discover -s tests -v
```

## Production image contract

`Dockerfile.production` requires `PYTHON_BASE_IMAGE` to be supplied as a
reviewed immutable digest. It uses a multi-stage virtual environment, copies no
tests or local state into the runtime image, runs as UID/GID 10001, and disables
access logs so request paths cannot become a second audit store. Its built-in
health check probes only the local `/healthz` endpoint. Build, scan, and push it
to ECR, then supply only the resulting ECR `@sha256:` reference to the plan-only
Terraform stack. The development Dockerfile remains for Compose.
