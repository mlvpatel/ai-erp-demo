# Local demo runbook

Use this runbook to prove the first AI ERP Demo workflow on a local machine.
It is intentionally centered on the service-operations MVP: request, work
order, technician closeout, parts issue, invoice-ready review, draft invoice,
and draft-only AI closeout proposal.

## 1. Prepare local configuration

```sh
cp development/.env.example development/.env
```

Change the local-only passwords and `AI_CONTROL_PLANE_SHARED_SECRET`. Keep the
checked-in Frappe/ERPNext commit pins and image digest pins unless you are
intentionally testing an upstream upgrade.

Check the local env:

```sh
scripts/dev.sh check-local-env
```

Print the local demo URL, login reminder, synthetic demo users, safe local
health hints, and next commands at any time:

```sh
scripts/dev.sh demo-info
```

## 2. Run static gates

```sh
scripts/dev.sh quality
scripts/dev.sh compose-config
```

## 3. Start and bootstrap the stack

```sh
scripts/dev.sh up
scripts/dev.sh bootstrap
```

Start the Frappe development server in a second terminal:

```sh
scripts/dev.sh bench-start
```

Open the Desk URL shown by `scripts/dev.sh demo-info`, normally
`http://ai-erp.localhost:8000/app`. Add `127.0.0.1 ai-erp.localhost` to
`/etc/hosts` if the host name does not resolve.

## 4. Prove the demo workflow

Create idempotent synthetic demo data:

```sh
scripts/dev.sh seed-demo
```

Run the Docker-backed checks:

```sh
scripts/dev.sh control-plane-test
scripts/dev.sh contract-test
scripts/dev.sh migrate
scripts/dev.sh service-test
scripts/dev.sh e2e-test
```

Or run the combined check:

```sh
scripts/dev.sh demo-check
```

The service-app integration suite proves:

- Service Location creation enforces its required Customer link,
- a Service Request creates a linked draft Service Work Order,
- a non-admin technician can work only within their allowed scope,
- manager-only closeout, parts issue, and draft-invoice controls hold,
- Stock Entry and Sales Invoice creation are idempotent,
- AI closeout proposals are cited, immutable, and review-only.

The source-of-truth acceptance map is `config/mvp-acceptance.json`. It links
the MVP acceptance metrics to concrete evidence files and verification commands.
The static quality gate runs `scripts/check-mvp-acceptance.py` so docs, tests,
and demo claims stay aligned.

The fresh-clone command contract is `config/fresh-clone-demo.json`. The static
quality gate runs `scripts/check-fresh-clone-demo.py` so this runbook,
`development/README.md`, `scripts/dev.sh`, the tracked `.env.example`, and the
Compose service map stay aligned.
The `demo-info` helper gives quick health hints for the env file, host mapping,
Docker CLI, and ignored local bench checkout without printing passwords,
tokens, raw environment values, absolute local paths, customer data, or private
prompts. The same static check executes `scripts/dev.sh demo-info` with tracked
and custom env-file paths to catch accidental leaks before publication.

The seed command creates synthetic master/demo records only: Customer, Service
Location, technician and manager users, demo part/labor items, an initial demo
Material Receipt for local stock, a Service Request, and a Scheduled Service
Work Order. It does not issue parts from the work order, create a Sales Invoice,
approve an AI proposal, or perform any AI-driven ERP mutation.

## 5. Manual UI walkthrough

After bootstrap and migration, use the Frappe desk to inspect:

- **Service Operations** workspace,
- **Service Request**,
- **Service Work Order**,
- **Service Closure Exception**,
- **AI Proposal**.

Use `docs/runbooks/demo-script.md` before creating a README screenshot, GIF,
maintainer walkthrough, or first public demo issue. It keeps the visible demo
story tied to MVP evidence, screenshot safety rules, and the same verification
commands used by this runbook.

Keep manual demo data synthetic. Do not enter real customer names, addresses,
phone numbers, invoices, attachments, credentials, or production exports.

## 6. Known local-only caveats

- Repository-owned code is `AGPL-3.0-only`; public release remains gated by
  source hygiene, GitHub CI, security contact, and fresh-clone verification.
- `development/frappe-bench/` is ignored local state and must never be committed.
- The default AI provider is a deterministic development template, not a hosted
  model adapter.
- If `development/.env` was created before digest pins were added, refresh it
  from `development/.env.example` before publishing demo results.
