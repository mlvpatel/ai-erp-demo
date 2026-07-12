# Pull request

## What changed?

<!-- Short summary of the user/business problem and the implementation. -->

## Scope

- [ ] Documentation only
- [ ] Horizontal core app (`apps/ai_erp_core`)
- [ ] Industry app (`apps/ai_erp_service` or another industry pack)
- [ ] AI control plane
- [ ] Contract/API/event schema
- [ ] Infrastructure/development tooling

## ERP and AI safety checks

- [ ] I did not modify or vendor upstream Frappe/ERPNext source.
- [ ] Money, stock, payroll, permissions, and compliance changes remain under
      deterministic ERP validation and authorized human/workflow approval.
- [ ] AI output is draft/proposal-only and includes source references where
      retrieval evidence exists.
- [ ] New or changed AI workflows were reviewed against
      `docs/security/ai-workflow-review.md`.
- [ ] Tenant/site boundaries and role permissions were considered.
- [ ] No secrets, customer exports, production backups, or private prompts are
      included.

## Tests and evidence

<!-- Paste focused commands and results. Use "not run" only with a reason. -->

- [ ] Unit tests
- [ ] Frappe integration tests
- [ ] Contract or schema checks
- [ ] Documentation reviewed

## Documentation

- [ ] README, docs, ADRs, workflows, or runbooks updated when behavior changed.
- [ ] New service, datastore, external provider, or irreversible dependency has
      an ADR.
