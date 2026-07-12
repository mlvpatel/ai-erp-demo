### AI ERP Core

Cross-industry policy and audit helpers for AI ERP Demo. It owns the
tenant-local `AI Proposal` ledger: a cited, immutable record of a draft-only
AI output, its policy result, model/prompt metadata, hashes, requester, and
human review. It never stores model credentials or makes a transactional ERP
change on behalf of an AI model.

### Local installation

This app is part of the AI ERP Demo monorepo. Use the root
`development/README.md` bootstrap flow; it links `apps/ai_erp_core` into the
local Frappe Bench checkout and installs it editable on the demo site.

If this app is later split into a standalone Frappe app repository, document
that repository URL and branch here as part of the split.

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/ai_erp_core
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

AGPL-3.0-only. See the repository root `LICENSE` file.
