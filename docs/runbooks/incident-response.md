# Incident response runbook

This runbook keeps security, data, and ERP-safety issues out of public channels
until they are understood. It applies to local development, demo publication,
and any future deployment that uses this repository.

## What counts as an incident

Treat the following as incidents:

- credentials, customer data, private prompts, production backups, database
  dumps, logs, or screenshots with sensitive data are committed, pasted, or
  attached publicly;
- AI output can create or submit stock, financial, payroll, access-control, or
  compliance changes without deterministic ERP validation and authorized human
  approval;
- a technician can perform manager-only closeout, stock issue, or invoice
  actions;
- a tenant/site boundary is bypassed;
- a restore, migration, connector, or workflow change corrupts ERP transaction
  links or audit evidence.

## First response

1. Stop copying, quoting, forwarding, or re-uploading the sensitive material.
2. Preserve the minimum private evidence needed to reproduce the issue.
3. Notify the repository owner or maintainer privately.
4. Rotate exposed secrets before continuing public work.
5. If the issue affects a real client environment, pause affected automation and
   follow the owner's legal, compliance, and customer-notification process.

## Triage checklist

Classify the incident privately:

- data class: secret, regulated/sensitive, business confidential, or synthetic;
- affected boundary: Frappe site, ERPNext transaction, custom app, AI control
  plane, connector/event contract, CI/release tooling, or documentation;
- impact: exposure only, unauthorized mutation, transaction corruption, service
  outage, or audit-evidence loss;
- observability evidence: alert name, metric name, trace identifier, log event
  identifier, and timestamp, with sensitive payloads removed;
- tenant scope: single site, multiple sites, or unknown;
- public exposure: local only, private repository, public issue/PR, release
  archive, or external service.

Do not paste raw logs, trace payloads, customer data, prompt bodies, or alert
routing secrets into public GitHub issues.

## Containment

- Remove leaked local files from the working tree and stop any pending source
  archive or release.
- If a secret is exposed, rotate it and invalidate sessions or tokens that used
  it.
- If production data, backups, or logs were committed, treat the history as
  contaminated until the owner approves a history rewrite or repository
  replacement.
- If AI can bypass approval, disable the affected AI workflow and keep ERP
  transactions under deterministic validation.
- If tenant isolation is uncertain, suspend cross-site integrations until the
  isolation check is repeated.

## Eradication and recovery

Before reopening public work:

1. Patch the root cause in code, configuration, documentation, or workflow.
2. Add a regression check when the leak or bypass path can recur.
3. Run the relevant focused check:
   - `python3 scripts/check-publication-secrets.py`
   - `scripts/check-publication-source.sh --strict`
   - `python3 scripts/check-tenant-isolation.py`
   - `python3 scripts/check-authorization-matrix.py`
   - `python3 scripts/check-transaction-safety.py`
   - `python3 scripts/check-audit-evidence.py`
   - `python3 scripts/check-operations-readiness.py`
   - `python3 scripts/check-observability-readiness.py`
4. Run `scripts/run-quality-gates.sh` before publication or release resumes.
5. Update the private incident notes with timeline, cause, impact, fix,
   verification, and remaining owner decisions.

## Public communication

Do not disclose vulnerability details publicly until a fix and disclosure date
are agreed. Public follow-up should be sanitized, avoid customer data, and link
to the fixed commit or release note only after the owner approves publication.
