# Operations readiness

Use this checklist before a demo is shared broadly, before a GitHub release, and
before anyone considers real client data. It keeps recovery, incident response,
and publication hygiene aligned with the ERP safety model.

## Readiness checklist

- `docs/runbooks/backup-restore.md` explains site-scoped backup and restore,
  restore-drill evidence, and backup artifact handling.
- `docs/runbooks/incident-response.md` explains private reporting,
  containment, AI approval-bypass handling, tenant-boundary handling, and safe
  public disclosure.
- `.gitignore`, `.gitattributes`, `scripts/check-publication-source.sh`, and
  `config/publication-secret-scan.json` all exclude local sites, logs, private
  files, database dumps, and backup artifacts.
- `SUPPORT.md` makes production use conditional on a backup/restore plan,
  deployment hardening, tenant-isolation review, and permission audit.
- `SECURITY.md` identifies any AI path to unapproved stock, financial, payroll,
  access-control, or compliance mutation as high priority.
- `docs/security/data-classification.md` keeps production backups, logs,
  customer data, and private prompts out of GitHub issues, pull requests,
  screenshots, test logs, and AI prompts.
- `docs/workflows/observability-readiness.md` names minimum monitoring signals
  and keeps logs, metrics, traces, screenshots, and alert examples free of
  customer data, prompt bodies, secrets, and backup URLs.
- `docs/workflows/performance-readiness.md` names the performance readiness
  profile for list/search/report, transaction, queue, and AI-draft paths.

## Pre-production gate

Do not use real customer, accounting, payroll, inventory, supplier, or employee
data until:

1. The root license and public support owner are resolved.
2. A deployment-specific backup/restore plan exists outside Git.
3. A restore drill has passed in a clean environment.
4. The threat model has been reviewed for the deployment.
5. Tenant isolation, role permissions, and approval workflows have fresh checks.
6. Secrets, backup encryption keys, database passwords, and provider keys live
   outside the repository.
7. Monitoring, logging, retention, and incident-response ownership are named.
8. `python3 scripts/check-observability-readiness.py` passes.
9. `python3 scripts/check-performance-readiness.py` passes.

## Verification

Run:

```sh
python3 scripts/check-operations-readiness.py
scripts/run-quality-gates.sh
```

The checker is intentionally static. It proves the public repository keeps the
right recovery and incident boundaries. A real deployment still needs an
environment-specific restore drill and private operations evidence.
