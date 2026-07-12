# Local Frappe/ERPNext development

This directory contains only the reproducible development configuration. The
actual Frappe Bench checkout and database state are intentionally ignored.

## First startup

1. From the repository root, copy `.env.example` to `.env` and replace the
   local-only passwords and the control-plane service secret:

   ```sh
   cp development/.env.example development/.env
   ```

   Keep the checked-in `FRAPPE_COMMIT` and `ERPNEXT_COMMIT` values unless you
   are intentionally testing an upstream upgrade. For that path, follow
   `docs/workflows/upstream-upgrade-readiness.md`.
2. From the repository root, start the development services:

   ```sh
   docker compose --env-file development/.env \
     -f infra/compose/docker-compose.dev.yml up -d
   ```

3. Bootstrap Frappe and an ERPNext site inside the development container. The
   script clones the configured `FRAPPE_BRANCH`, installs ERPNext from
   `apps.json`, pins Frappe and ERPNext to the configured commits, links the
   monorepo custom apps into Bench, installs them editable, and installs
   `ai_erp_core` and `ai_erp_service` on the site:

   ```sh
   docker compose --env-file development/.env \
     -f infra/compose/docker-compose.dev.yml exec frappe \
     bash /workspace/scripts/bootstrap-frappe-dev.sh
   ```

4. Start the Frappe development processes in a second terminal:

   ```sh
   docker compose --env-file development/.env \
     -f infra/compose/docker-compose.dev.yml exec frappe \
     bash -lc 'cd /workspace/development/frappe-bench && bench start'
   ```

Open `http://ai-erp.localhost:8000/app`. Add an `/etc/hosts` entry for
`127.0.0.1 ai-erp.localhost` if the browser cannot resolve the site name.

The same commands are wrapped by `scripts/dev.sh`; run `scripts/dev.sh help`
from the repository root for the command list, or `scripts/dev.sh demo-info`
for the local Desk URL, login reminder, synthetic demo users, and next demo
commands.

## Upstream pins

The tracked defaults currently pin the local ERP base to:

- Frappe `7699c7feefac77a36853d3a955d9b6b53552f55e`
- ERPNext `d1d3b241ae7bc21d18cf830a4bacd568e21a2a19`
- Frappe Bench image
  `frappe/bench@sha256:339ff7ad224304c566b4f468e19f3aba299deaf5b82b13beb50ebe95dd477d2c`
- MariaDB image
  `mariadb@sha256:efb4959ef2c835cd735dbc388eb9ad6aab0c78dd64febcd51bc17481111890c4`
- Redis image
  `redis@sha256:2cc044fc5a07c9b701f8f1255a309ae9ad7856e694ac03513bf3648c01e40763`

`FRAPPE_BRANCH=version-16` remains in the environment because Bench needs a
branch for the initial clone. The commit variables are the reproducibility
gate. If an ignored upstream checkout already exists at a different commit and
has local changes, `scripts/bootstrap-frappe-dev.sh` stops instead of
overwriting those changes. Image variables are digest-pinned so the local
runtime does not silently change when a registry tag moves.

After changing a custom app, apply its schema and run the focused service MVP
test suite:

```sh
docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec \
  --workdir /workspace/development/frappe-bench frappe \
  bench --site ai-erp.localhost migrate

docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec \
  --workdir /workspace/development/frappe-bench frappe \
  bench --site ai-erp.localhost set-config allow_tests true

docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec \
  --workdir /workspace/development/frappe-bench frappe \
  bench --site ai-erp.localhost run-tests --app ai_erp_service \
  --doctype "Service Work Order" --test-category integration --failfast
```

The compose stack also starts an internal-only, stateless AI control plane. The
default `template` renderer is a deterministic development aid, not a hosted
model. After migrating `ai_erp_core` and `ai_erp_service`, assign **AI Proposal
Requester** to users who should view their own drafts and **AI Proposal
Approver** to users who can record a human review. Then a technician or Service
Manager can use **Draft AI Closeout Summary** from a submitted work order. The
recorded approval has no ERP side effect.

Run the control-plane unit suite with:

```sh
docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec ai-control-plane \
  python -m unittest discover -s tests -v
```

Seed synthetic local demo data with:

```sh
scripts/dev.sh seed-demo
```

The seed is idempotent and local-only. It creates demo master data, initial demo
stock, a Service Request, and a Scheduled Service Work Order, but it does not
issue work-order parts, draft an invoice, or approve an AI proposal.

## Safety

- This is a local development environment only; do not use its credentials or
  volumes in production.
- Keep all upstream Frappe and ERPNext source under the ignored Bench folder.
- Update `FRAPPE_COMMIT`, `ERPNEXT_COMMIT`, and image digest variables together
  with a focused migration and integration-test run when intentionally
  upgrading the ERP base. Follow `docs/workflows/upstream-upgrade-readiness.md`
  before merging the change.
- Run `scripts/check-reproducibility.sh` before publishing a development-config
  change.
- Generate and install custom apps only after the base site health check passes.
- Keep custom apps linked from `/workspace/apps/`; do not copy them into the
  ignored Bench checkout.
- Use the site-specific `bench --site ai-erp.localhost ...` form for migrations
  and tests.
