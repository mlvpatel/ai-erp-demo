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

## Development renderer

The only renderer currently implemented is `template`. It deterministically
formats submitted closeout fields and identifies itself as
`development-template` in every response. It is useful for running the entire
approval/audit path locally, but it is not represented as a production AI
model. There is deliberately no implicit cloud-model fallback.

Adding a production provider requires a new approved adapter, documented data
handling, prompt/version tracking, evaluation, and tests. It must still return
the existing draft-only contract; it must never receive ERP database credentials
or invoke an ERP write endpoint.

## Local checks

```sh
docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec ai-control-plane \
  python -m unittest discover -s tests -v
```
