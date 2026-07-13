# Security policy

This repository is a development demo, not a production deployment. Do not
file secrets, customer data, database dumps, or private model prompts in an
issue or pull request.

For a suspected vulnerability, use the repository's
[private GitHub Security Advisory form](https://github.com/mlvpatel/ai-erp-demo/security/advisories/new)
with a minimal reproduction and affected commit. Do not open a public issue or
share the report elsewhere. Do not disclose the issue publicly until a fix and
disclosure date have been agreed.

The AI control plane is intentionally draft-only. A report that demonstrates a
path from AI output to an unapproved stock, financial, payroll, access-control,
or compliance mutation is a high-priority security issue.

Design-time security guidance lives in `docs/security/`, including the MVP
threat model and data-classification policy.

Incident handling guidance lives in `docs/runbooks/incident-response.md`. Do
not attach database dumps, production backups, customer data, logs, private
prompts, credentials, or screenshots with sensitive data to public issues or
pull requests.
