# Support

AI ERP Demo is a development-stage open-source project. It is not production
support for ERPNext, Frappe, accounting, tax, payroll, legal compliance, or
hosted operations.

## Good places to ask for help

- Use GitHub issues for reproducible bugs, documentation gaps, and scoped
  feature proposals.
- Use the local demo runbook for setup checks:
  `docs/runbooks/local-demo.md`.
- Use the GitHub publication runbook before making the repository public:
  `docs/runbooks/github-publication.md`.
- Use the backup/restore and incident runbooks before any real client data or
  recovery drill:
  `docs/runbooks/backup-restore.md` and
  `docs/runbooks/incident-response.md`.

## What to include in a bug report

- The command or workflow you ran.
- Expected behavior and actual behavior.
- Relevant logs or screenshots, with secrets removed.
- Whether the problem is in the Frappe/ERP stack, the service industry app, the
  AI control plane, or repository tooling.

## Security and private data

Do not open public issues containing credentials, customer data, database dumps,
private prompts, or vulnerability details. Follow `SECURITY.md` for suspected
security issues.

## Production use

Before using this project for a real client, complete the threat model review,
backup/restore plan, deployment hardening, and a fresh tenant-isolation and
permission audit. Use the demo legal-readiness package under
`docs/compliance/` (start with `owner-fill-in-checklist.md`, then privacy
inventory, DPA/DPIA templates, go/no-go checklist) as the counsel and owner
checklist. Those files are templates and gates, not legal approval or GDPR
compliance.
