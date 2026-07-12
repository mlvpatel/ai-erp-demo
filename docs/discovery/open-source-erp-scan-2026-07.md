# Open-source ERP GitHub scan

- Review date: 2026-07-10
- Purpose: learn from mature open-source ERP repositories before shaping AI ERP
  Demo's architecture and public repo structure.
- Method: inspect public GitHub repository pages and license files where
  available. Stars and releases are point-in-time signals, not product quality
  guarantees.

## Summary

ERPNext/Frappe is the selected MVP base because it combines broad ERP coverage,
an app-extension model, Python/JavaScript implementation, active v16 releases,
and a development workflow that lets this repo keep upstream ERP source out of
Git while building custom industry packs.

Odoo has the largest GitHub community footprint and should remain the benchmark
for breadth and polish. Dolibarr is a good simplicity benchmark. Tryton is a
Pythonic architecture benchmark. Axelor, iDempiere, and metasfresh are useful
for enterprise workflow and manufacturing/reference architecture ideas, but are
heavier first choices for this AI-first demo.

## Repository comparison

| Repository | Observed GitHub signal | Stack/license notes | What to learn | Why not chosen as MVP base |
| --- | --- | --- | --- | --- |
| ERPNext | 36.7k stars, v16.26.2 latest on 2026-07-10 | Python/JavaScript ERP on Frappe; GPL-3.0 license in upstream ERPNext. | Module breadth, DocTypes, workflows, permissions, accounting/stock reuse. | Chosen base. |
| Frappe | 10.4k stars, v16.26.3 latest on 2026-07-10 | Python/JavaScript low-code framework; MIT license in upstream framework. | Custom app model, REST API, permissions, jobs, multitenant site model. | Chosen framework. |
| Odoo | 52.9k stars, 33.1k forks | Python/JavaScript business apps; license file says LGPLv3 for Odoo source. | Benchmark breadth, marketplace strategy, polished business UX. | Strong option, but less aligned with this repo's ERPNext/Frappe custom-app direction and current local proof. |
| Dolibarr | 7.4k stars, 3.5k forks | PHP; supports MariaDB, MySQL, or PostgreSQL. | Simpler install, small-business UX, modular toggles. | Too small-business/simple for the first AI-governed service workflow and less aligned with Python AI tooling. |
| Tryton | 203 stars on GitHub mirror, 13k+ tags | Python; GitHub repository is a mirror of the primary Tryton code host. | Clean Python ERP concepts and modular packages. | GitHub mirror makes it less direct for a GitHub-first public repo benchmark. |
| iDempiere | 635 stars | Java/Eclipse/OSGi lineage; full ERP/CRM/MFG/SCM/POS positioning. | Enterprise process depth and plugin discipline. | Heavier runtime and contributor experience than needed for the MVP. |
| metasfresh | 2.4k stars, latest GitHub release shown as 2023 | Java/Spring Boot/PostgreSQL/React topics. | Manufacturing, sales, shipping, invoice workflow references. | Heavier architecture and less current release signal on GitHub. |
| Axelor Open Suite | 960 stars, v9.1.2 latest on 2026-07-02 | Built on Axelor Open Platform; modules include CRM, sales, finance, HR, projects, inventory, production, multi-company, multi-currency, and multilingual support. | Modular enterprise app suite and workflow coverage. | Good active alternative, but a Java/Groovy/Gradle ecosystem would slow the current Python/Frappe AI ERP path. |

## Patterns to copy

- Keep upstream ERP source separate from custom extensions.
- Make installation and local development explicit.
- Publish issue templates that ask for business context, not just technical
  symptoms.
- Treat security reporting as first-class.
- Keep the first workflow demonstrable end to end before expanding modules.
- Use strong module boundaries so industry packs can be added without turning
  the repo into one giant custom app.

## Patterns to avoid

- A generic `frontend/` and `backend/` split when the ERP framework already
  provides the product shell and API.
- Broad industry claims without one working vertical workflow.
- AI agents that directly mutate accounting, inventory, payroll, permissions,
  or compliance records.
- Vendoring upstream ERP code into this repository.
- Auto-upgrading framework tags without migration and integration evidence.

## Decision impact

The scan supports the existing architecture:

- `apps/ai_erp_core/` for cross-industry AI policy and proposal audit.
- `apps/ai_erp_service/` for the first industry pack.
- Future industry packs only after discovery proves a workflow.
- `services/ai_control_plane/` for provider-independent AI orchestration.
- `contracts/` for public API/event boundaries.

## Sources

- ERPNext: <https://github.com/frappe/erpnext>
- Frappe Framework: <https://github.com/frappe/frappe>
- Odoo: <https://github.com/odoo/odoo>
- Odoo license: <https://raw.githubusercontent.com/odoo/odoo/19.0/LICENSE>
- Dolibarr: <https://github.com/Dolibarr/dolibarr>
- Tryton mirror: <https://github.com/tryton/tryton>
- iDempiere: <https://github.com/idempiere/idempiere>
- metasfresh: <https://github.com/metasfresh/metasfresh>
- Axelor Open Suite: <https://github.com/axelor/axelor-open-suite>

