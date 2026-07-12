# AI ERP working rules

## Architecture

- Read `.agents/skills/ai-erp-delivery/SKILL.md` before work that changes or
  reviews an ERP feature, AI workflow, integration, contract, or ERP delivery
  document.
- Read `.agents/skills/erp-minimal-change/SKILL.md` before implementation,
  refactoring, or dependency decisions. Its minimal-change rule is subordinate
  to ERP safety, correctness, tenant isolation, audit, contract, and testing
  requirements.
- Use ERPNext/Frappe as the upstream ERP platform; add custom behaviour only in
  `apps/`.
- Never patch or vendor upstream Frappe/ERPNext source into this repository.
- Put broadly reusable behaviour in `apps/ai_erp_core/`; keep sector-specific
  features in an industry app.
- Keep model-provider calls, prompt handling, retrieval, and evaluation inside
  `services/ai_control_plane/`.
- Version every external API and business event under `contracts/`.

## Safety

- AI must not directly create or post financial, inventory, payroll, or access
  control changes. It returns a proposed action for deterministic validation and
  human approval.
- Never place secrets, personal data, customer exports, or production backups in
  this repository.
- Preserve tenant isolation and role-based access checks at every API boundary.

## Engineering

- Write an ADR in `docs/adr/` before introducing a new service, datastore, or
  external dependency.
- Add tests in the matching `tests/` directory with every feature.
- Prefer a modular monolith and Frappe's built-in jobs before adding distributed
  infrastructure.
- Keep documentation concise and update it with behavior-changing code.
