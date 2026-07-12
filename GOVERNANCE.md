# Governance

This repository is currently an owner-led MVP. Governance should stay lightweight
until there are regular external contributors, but the decision boundaries must
be explicit because ERP and AI changes can create financial, inventory,
security, or compliance risk.

## Decision model

- The repository owner makes final product, licensing, and publication
  decisions until a named maintainer group is created.
- Architecture changes that add a service, datastore, external provider, or
  irreversible dependency require an ADR in `docs/adr/`.
- Feature work must stay inside the project boundaries in `AGENTS.md`.
- AI may draft, summarize, classify, retrieve, or propose. It must not directly
  post money, stock, payroll, permission, or compliance changes.

## Maintainer responsibilities

- Keep upstream Frappe/ERPNext source out of this repository.
- Review changes for tenant isolation, role permissions, auditability, and
  deterministic ERP transaction boundaries.
- Require tests for behavior changes and contract tests for public interfaces.
- Keep documentation truthful about what is implemented versus planned.
- Avoid accepting customer data, secrets, production backups, or private prompts
  into issues, pull requests, examples, or fixtures.

## Contribution acceptance

Maintainers may decline contributions that are useful in isolation but increase
ERP safety risk, bypass Frappe/ERPNext upgrade boundaries, add speculative
infrastructure, or weaken the AI approval model.

Repository-owned code is licensed under `AGPL-3.0-only`. External contributions
must include DCO sign-off and preserve the ERP safety, tenant, audit, and AI
approval boundaries described in `AGENTS.md`.
