# Backup and restore runbook

This runbook is a pre-production baseline for the AI ERP Demo. It does not turn
the project into a hosted production service; it defines the minimum recovery
discipline required before any real client data is used.

Use the official Frappe Bench backup and restore commands, keep every backup
site-scoped, and never commit backup artifacts to this repository.

## Scope and safety rules

- One tenant maps to one Frappe site. Back up and restore one site at a time.
- Treat database dumps, file archives, site configs, logs, and restore notes as
  sensitive operational evidence.
- Keep backups outside Git. The repository ignores and export-ignores
  `*.sql`, `*.sql.gz`, `*.dump`, `*.backup`, `*-files.tar`, and
  `*-private-files.tar`.
- Store production backup encryption keys, database credentials, and object
  storage credentials in the deployment platform or a secrets manager, never in
  `.env`, docs, issues, screenshots, or AI prompts.
- Before restoring into any shared environment, confirm the target site,
  database name, app versions, ERPNext/Frappe pins, and owner approval.
- The AI control plane is stateless for the MVP. Restore proof must focus on
  Frappe site data, ERPNext transactions, custom app DocTypes, files, and audit
  records.

## Create a backup

From the bench root for the target deployment, run:

```sh
bench --site <site> backup --with-files
```

The Frappe default location is under the site private backup folder. Move the
backup set to approved encrypted storage after creation; do not copy it into the
project root.

Record the following in the private operations log, not in Git:

- site name and tenant/customer owner,
- timestamp and operator,
- app versions and commit identifiers,
- database backup path,
- public-files archive path,
- private-files archive path,
- encryption/storage location,
- checksum for each backup artifact.

## Restore drill

Run a restore drill before production use, before major upgrades, and after any
change that affects DocTypes, permissions, invoices, stock, payroll, or AI audit
records.

For the AWS pilot, use the protected
`.github/workflows/production-restore-drill.yml` workflow and select only a
manifest written last by the verified backup task. It generates a
`restore-drill-*.internal` site, never targets the production hostname, verifies
all database/configuration/public/private artifact checksums, uses the official
Bench restore options below, runs payload-free integrity checks, and deletes the
site and database with `drop-site --no-backup --force`. The workflow stores only
aggregate private evidence; the manifest URI and restored data stay out of Git.

Restore into a clean non-production site first:

```sh
bench --site <site> restore <path/to/database.sql.gz> \
  --with-public-files <path/to/public-files.tar> \
  --with-private-files <path/to/private-files.tar>
```

After restore, run:

```sh
bench --site <site> migrate
```

Then verify:

1. The restored site opens and has the expected installed apps.
2. Custom DocTypes from `ai_erp_core` and `ai_erp_service` exist.
3. Role permissions still separate technician and manager actions.
4. A restored Service Work Order keeps stock and invoice links immutable.
5. AI Proposal records keep model metadata, source hashes, review metadata, and
   ERP record links.
6. Attachments and private files are readable only by authorized roles.
7. No restored site, logs, database dumps, or backup artifacts appear in the
   publishable repository tree.

## Recovery acceptance

A backup/restore plan is not accepted until:

- at least one restore drill has completed in a clean environment,
- the drill verifies role permissions, tenant isolation, transaction links, and
  AI audit evidence,
- the recovery point objective and recovery time objective are named for the
  deployment,
- backup retention and deletion rules are documented privately for the owner,
- restore credentials and encryption keys are stored outside the repository,
- `python3 scripts/check-operations-readiness.py` passes.

## Failure handling

If a restore fails or restored data looks inconsistent:

1. Stop the restore attempt and preserve the failed environment for private
   diagnosis.
2. Do not paste dumps, tracebacks with secrets, customer records, or screenshots
   into public GitHub issues.
3. Follow `docs/runbooks/incident-response.md` if data exposure, permission
   bypass, AI approval bypass, or transaction corruption is possible.
4. Open a sanitized bug only after sensitive details are removed.
