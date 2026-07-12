# Contributing

Thank you for helping build AI ERP Demo.

Please follow `CODE_OF_CONDUCT.md`, `SECURITY.md`, and `GOVERNANCE.md`.
Contributions are licensed under `AGPL-3.0-only`. Every commit must include a
Developer Certificate of Origin sign-off (`git commit -s`) confirming that the
contributor has the right to submit the work under this license.
Use `BACKLOG.md` to choose small, safe starter issues.

Before changing an ERP feature, read the repository `AGENTS.md` and the two
repo-local delivery skills under `.agents/skills/`. Keep Frappe/ERPNext source
upstream; custom behavior belongs in `apps/`, provider and prompt code belongs
in `services/ai_control_plane/`, and public schemas belong in `contracts/`.

Every behavior change needs a focused test and a concise documentation update.
AI changes must retain source citations, tenant/site scope, policy evaluation,
human approval, and an explicit proof that no unauthorized ERP transaction is
created. Never submit credentials, customer exports, production backups, or
model prompts containing personal data.

The local test commands are in [development/README.md](development/README.md).
