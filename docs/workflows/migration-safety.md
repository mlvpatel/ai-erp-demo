# Migration safety

ERP schema and fixture changes must stay boring, reviewable, and Frappe-native.
The MVP uses Frappe app metadata, DocType JSON, fixtures, and `bench migrate`;
it does not use ad-hoc schema DDL in application code.

## MVP migration rules

- Put DocType changes in the owning Frappe app under `apps/*/*/*/doctype/`.
- Put exported role/custom-field fixtures behind each app's `fixtures` list.
- Keep app `patches.txt` files empty unless a maintainer-approved data
  migration is necessary.
- Do not run `ALTER TABLE`, `CREATE TABLE`, `DROP TABLE`, `TRUNCATE TABLE`, or
  `RENAME TABLE` from custom app code.
- Use `bench --site ... migrate` before seeding demo data or running service
  integration tests.
- For Frappe/ERPNext pin or runtime image updates, prove migration plus the
  service workflow integration gate before claiming the update is safe. Also
  follow the upstream upgrade readiness workflow in
  `docs/workflows/upstream-upgrade-readiness.md`.

## When a real patch is needed

Add a Frappe patch only when DocType JSON, fixtures, and deterministic runtime
validation cannot handle the change. A patch PR must include:

1. the exact affected DocTypes and fields,
2. idempotency behavior on retry,
3. rollback or recovery notes,
4. synthetic test data only,
5. a migration run before the service workflow test.

The machine-readable migration safety contract is
`config/migration-safety.json`. The static quality gate runs
`scripts/check-migration-safety.py` so helper commands, docs, app metadata,
empty patch files, and forbidden schema shortcuts remain aligned.
