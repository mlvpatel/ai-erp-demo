# Upstream upgrade readiness

Use this workflow before changing Frappe, ERPNext, Frappe Bench, MariaDB, Redis,
Python, or any runtime image digest. The AI ERP Demo depends on ERPNext/Frappe
for accounting, stock, permissions, workflows, reports, jobs, and audit
history, so upstream upgrades are product-risk changes, not routine dependency
chores.

## Non-negotiable boundaries

- Never patch or vendor upstream Frappe/ERPNext source into this repository.
- Keep upstream checkouts under ignored `development/frappe-bench/`.
- Keep `FRAPPE_COMMIT` and `ERPNEXT_COMMIT` pinned to full 40-character commit
  hashes in `development/.env.example`.
- Keep `MARIADB_IMAGE`, `REDIS_IMAGE`, and `FRAPPE_BENCH_IMAGE`
  digest-pinned.
- Do not auto-merge Frappe/ERPNext pin changes, runtime image digest changes,
  or branch changes.
- Change one upstream axis at a time unless the release notes require a paired
  move. Record the pairing explicitly in the PR.

## Required preparation

Before editing pins:

1. Read upstream Frappe and ERPNext release notes or commits for breaking
   changes affecting DocTypes, workflows, permissions, background jobs, REST
   APIs, reports, stock, selling, accounting, or patches.
2. Confirm the target Frappe and ERPNext commits belong to compatible branches.
3. Check whether MariaDB, Redis, Python, Node, or Frappe Bench image changes
   are required by the target upstream commits.
4. Review `docs/workflows/migration-safety.md`,
   `docs/workflows/transaction-safety.md`,
   `docs/workflows/authorization-and-approvals.md`,
   `docs/workflows/tenant-isolation.md`, and
   `docs/workflows/performance-readiness.md`.
5. Record rollback notes: previous commits, previous image digests, migration
   impact, and whether a restore drill is needed.

## Local validation sequence

Run the validation in this order:

```sh
scripts/check-reproducibility.sh
docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml config --quiet
scripts/dev.sh migrate
scripts/dev.sh seed-demo
scripts/dev.sh demo-check
scripts/dev.sh control-plane-test
scripts/dev.sh contract-test
scripts/dev.sh service-test
python3 scripts/check-upstream-upgrade-readiness.py
scripts/run-quality-gates.sh
```

If the local Frappe Bench checkout already exists with local changes,
`scripts/bootstrap-frappe-dev.sh` must stop instead of overwriting upstream
source. Resolve that outside the publication tree.

## Evidence to include in the PR

- Old and new Frappe commit.
- Old and new ERPNext commit.
- Old and new image digests if any image changed.
- Upstream release note or commit links reviewed.
- Migration result.
- Service workflow integration result.
- Control-plane and contract-test result.
- Demo seed and demo-check result.
- Any performance-readiness impact for list/search/report, queue, stock,
  invoice, or AI proposal paths.
- Rollback plan.

## Do not claim success until

- Custom apps still install without patching upstream.
- `bench --site ... migrate` succeeds on a clean site.
- Technician and manager role boundaries still hold.
- Stock issue and draft Sales Invoice actions remain idempotent.
- AI Proposal approval still has no ERP transaction side effect.
- Tenant isolation remains one Frappe site/database per tenant.
- Publication checks still prove upstream source is not vendored.
- Public docs mention any changed runtime assumptions honestly.
