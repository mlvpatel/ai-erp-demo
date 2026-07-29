# Data classification and AI-sharing policy

This repository must be safe to publish and safe for contributors to run with
synthetic data. Do not commit real customer, employee, supplier, payroll,
accounting, stock, or production system data.

## Classification levels

| Level | Examples | GitHub allowed? | AI control plane allowed? |
| --- | --- | --- | --- |
| Public project data | README text, architecture docs, synthetic fixtures, public API schemas. | Yes. | Yes, if relevant. |
| Internal design data | Non-secret roadmap notes, design decisions, synthetic business examples. | Yes. | Yes, if relevant. |
| Business confidential | Real customer names, contacts, service addresses, supplier pricing, quotes, invoices, stock levels, employee records. | No. | Only through an explicit allow-list in a local/dev workflow; never in public fixtures. |
| Regulated/sensitive | Payroll, bank details, tax filings, credentials, access tokens, private prompts, production backups, trace exports, observability exports, health/safety reports. | Never. | No for the MVP. |
| Secrets | API keys, model keys, database passwords, SSH keys, cookies, encryption keys. | Never. | Never as prompt/context data. |

## Repository rules

- Use only synthetic fixtures and examples.
- Keep `.env`, `.env.*`, `development/.env`, `development/frappe-bench/`,
  local sites, logs, private files, database dump and backup artifacts, and
  backups out of Git.
- Treat `*.sql`, `*.sql.gz`, `*.dump`, `*.backup`, `*-files.tar`, and
  `*-private-files.tar` as local-only recovery artifacts.
- Keep production observability exports, raw logs, trace payloads, dashboard
  screenshots with customer data, alert routing secrets, prompt bodies, and
  provider responses out of Git.
- Do not paste secrets or customer data into issues, pull requests, screenshots,
  test logs, or AI prompts.
- If a test needs a realistic value, invent one and mark it as synthetic.
- Run `python3 scripts/check-publication-secrets.py` before publication or
  after changing fixtures, examples, issue templates, or publication docs.

## AI-control-plane sharing rules

The first AI workflow may receive only the fields needed to draft a closeout
summary:

- service work order identifier,
- subject,
- description,
- closeout notes,
- typed time rows,
- typed part rows,
- source labels and source hashes.

The first AI workflow must not receive:

- attachment contents,
- customer contact details,
- service addresses,
- model/provider keys,
- database credentials,
- payroll data,
- bank/tax identifiers,
- private prompt text from another tenant,
- stock valuation or accounting ledgers unless a future ADR and allow-list
  explicitly permit them.

## Synthetic fixture policy

Synthetic fixtures should be:

- small enough to review manually,
- clearly fake,
- deterministic in tests,
- free of real names, phone numbers, emails, addresses, tax IDs, API keys, and
  production-like secrets,
- connected to an acceptance test or demo workflow.

## Incident handling inside the repo

If sensitive data is committed or pasted:

1. Stop copying or quoting it.
2. Notify the repository owner privately.
3. Rotate any exposed secret.
4. Remove the data from the working tree and history before publication.
5. Add a regression check or documentation update if the leak path can recur.

For the broader demo legal-readiness package (inventory, counsel templates,
go/no-go checklist), see `docs/compliance/README.md`. Those files do not make
the repository GDPR compliant.
