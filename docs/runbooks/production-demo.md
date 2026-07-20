# Production-style local demo

This runbook starts the production images locally so the demo behaves the way
a deployment would: an nginx frontend, gunicorn web workers, a websocket
process, background queue workers, a scheduler, TLS to MariaDB, and the
hardened read-only AI control plane. Everything stays synthetic and free: no
cloud account, hosted model, or billable credential is involved, and a passing
run is technical evidence, not production, capacity, or human-acceptance
evidence.

## Start

```sh
docker compose --env-file development/.env \
  -f infra/compose/docker-compose.demo.yml up -d --build
```

The one-shot `cert-init`, `configurator`, and `migrator` services generate a
local CA for the database TLS chain, create the `ai-erp-demo.localhost` site
with all apps, and run migrations before the long-running services start.

## Seed

```sh
docker compose --env-file development/.env \
  -f infra/compose/docker-compose.demo.yml exec \
  -e AI_ERP_LOCAL_SETUP_ALLOW=1 web \
  bench --site ai-erp-demo.localhost execute \
  ai_erp_service.demo_seed.initialize_local_demo_site

docker compose --env-file development/.env \
  -f infra/compose/docker-compose.demo.yml exec web \
  bench --site ai-erp-demo.localhost execute \
  ai_erp_service.demo_seed.seed_rich_demo
```

`seed_rich_demo` layers a bounded synthetic portfolio over the base seed:
twelve customers with plant locations, seventy-two work orders spread across
the workflow statuses, and a few cannot-close blockers with owned exceptions.
Re-runs skip existing records, and the layer never issues parts, drafts an
invoice, or performs an AI mutation, so a presenter drives every transaction
live.

## Open

Visit `http://localhost:8081` and sign in as `Administrator` with
`DEMO_ADMIN_PASSWORD` from `development/.env`. Follow
`docs/runbooks/demo-script.md` for the presented journey; the profitability
report, evidence replay, scheduling suggestions, and draft-only AI proposals
all run against this stack.

## Reset

```sh
docker compose --env-file development/.env \
  -f infra/compose/docker-compose.demo.yml down -v
```

`down -v` removes the site, database, certificates, and queues so the next
start is a fresh, reproducible demo.

## Boundaries

- The `frappe/erpnext` base tag and `python` base tag in the compose file are
  local demo pins. Release builds keep using the digest-pinned protected
  variables with signing, SBOM, and scan evidence.
- The stack runs one site on one machine. It is not a deployment, makes no
  availability promise, and produces no public capacity claim.
