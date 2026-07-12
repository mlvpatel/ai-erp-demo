# July 2026 technology stack decision

- Review date: 2026-07-10
- Status: Accepted for MVP
- Scope: AI ERP Demo open-source repository and local developer stack

## Recommendation

Use ERPNext/Frappe v16 as the transactional ERP platform, with custom Frappe
apps for product differentiation and a small isolated FastAPI AI control plane
for draft-only AI workflows.

This is intentionally not a generic `frontend` plus `backend` architecture.
ERPNext/Frappe already supplies the business UI, document model, permissions,
workflows, reports, REST API, audit trail, background jobs, and real-time
events. The custom code should focus on industry workflows and governed AI
assistance.

## Stack

| Layer | Choice | Why |
| --- | --- | --- |
| ERP core | ERPNext v16 on Frappe v16 | Mature open-source ERP modules for accounting, stock, selling, projects, manufacturing, assets, CRM, users, roles, and audit. |
| Custom ERP behavior | Frappe apps under `apps/` | Keeps upstream ERPNext clean while allowing industry packs and shared AI governance. |
| First database | MariaDB | Current ERPNext development path is proven locally on MariaDB; PostgreSQL remains a future technical spike, not the MVP default. |
| Cache/queue/realtime | Redis through Frappe Bench | Reuses the Frappe runtime instead of adding separate distributed infrastructure. |
| AI service | FastAPI under `services/ai_control_plane/` | Small, testable boundary for prompt rendering, provider adapters, tool policies, citations, and evaluation. |
| API contracts | OpenAPI under `contracts/openapi/` | External AI/service boundaries stay versioned before integrations depend on them. |
| Local runtime | Docker Compose with digest-pinned images | Reproducible enough for open-source contributors without introducing Kubernetes before production requirements exist. |
| Testing | Python unit tests plus focused Frappe integration tests | Proves deterministic AI control-plane behavior and the high-risk ERP transaction boundaries. |
| Repo automation | GitHub Actions | Runs lightweight checks on pull requests and keeps publication gates visible. |

## July 2026 upstream evidence

- ERPNext's GitHub repository positions it as a free and open-source ERP and
  lists core areas including accounting, order management, manufacturing,
  assets, and projects.
- ERPNext's GitHub repository showed 36.7k stars and latest release v16.26.2 on
  2026-07-10.
- Frappe's GitHub repository describes the framework as a low-code web
  framework in Python and JavaScript, lists topics including REST API, MariaDB,
  Postgres, multitenancy, and low-code, and showed latest release v16.26.3 on
  2026-07-10.
- The local repository remains pinned to tested Frappe/ERPNext commits instead
  of automatically chasing the latest tag. Upgrade pins only after migration and
  integration checks pass.

## Why not a greenfield ERP stack?

Building accounting, stock, tax, permissions, workflows, audit history, and
multi-company business records from scratch would consume the MVP before the AI
ERP differentiation starts. It would also increase the chance of unsafe AI
actions because the project would need to invent its own transaction controls.

## Why not use Odoo as the base?

Odoo has the largest GitHub footprint in the scan and a broad module ecosystem.
It remains a serious comparison point. For this repo, ERPNext/Frappe wins the
MVP because it gives a clean custom-app model, strong Python ergonomics, an
open-source-first positioning, and a direct path to keep upstream ERP source out
of our repository.

## Why not use Dolibarr, Tryton, iDempiere, metasfresh, or Axelor first?

Each is useful in a different niche, but none is a better first base for this
specific AI ERP demo:

- Dolibarr is simpler and PHP-based, good for small-business ERP/CRM, but less
  aligned with a Python AI control plane and deep custom DocType workflow.
- Tryton is Pythonic and clean, but the GitHub repository is a mirror and has a
  smaller GitHub community footprint.
- iDempiere and metasfresh are Java-heavy and more complex for a lightweight
  AI-assisted open-source demo.
- Axelor is modular and active, but adopting it would move the project into a
  Java/Groovy/Gradle ecosystem instead of the Python/Frappe path already proven
  by the local stack.

## Upgrade rule

Do not update Frappe, ERPNext, MariaDB, Redis, or image digests only because a
new tag exists. Update them together with:

- a short note in `development/README.md`,
- a passing `scripts/check-reproducibility.sh`,
- a Docker Compose config check,
- a site migration,
- focused service integration tests, and
- an explanation of why the upgrade matters.

## Sources

- ERPNext GitHub repository: <https://github.com/frappe/erpnext>
- Frappe GitHub repository: <https://github.com/frappe/frappe>
- Odoo GitHub repository: <https://github.com/odoo/odoo>
- Dolibarr GitHub repository: <https://github.com/Dolibarr/dolibarr>
- Tryton GitHub mirror: <https://github.com/tryton/tryton>
- iDempiere GitHub repository: <https://github.com/idempiere/idempiere>
- metasfresh GitHub repository: <https://github.com/metasfresh/metasfresh>
- Axelor Open Suite GitHub repository:
  <https://github.com/axelor/axelor-open-suite>

