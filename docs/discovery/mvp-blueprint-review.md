# Review of the supplied AI ERP MVP blueprint

Review date: 2026-07-11

The blueprint's vertical-first strategy, modular-monolith preference, Docker
self-hosting goal, typed AI tools, human approval, and audit trail are adopted.

The greenfield FastAPI/Next.js/hand-built-ledger architecture is not adopted.
The product will use ERPNext/Frappe as the transactional core and implement
only the service-operations and AI differentiation as custom apps/services.

The MVP's lead vertical is service operations rather than generic professional
services because it has an available design partner and a reusable process
shape: request, work order, time/parts, closeout, and invoice readiness.

The blueprint's shared-PostgreSQL tenancy is replaced by a Frappe site/database
per tenant. PostgreSQL usage for ERPNext must be verified in the technical
spike; it is not a committed database decision.

The first AI feature remains draft-only: work-order closeout assistance or an
overdue-invoice reminder. Any external message or state-changing action requires
the ERP's validation and an authorized approval.

## Decision map

| Blueprint recommendation | Project decision | Reason |
| --- | --- | --- |
| Do not build a generic all-industry ERP from scratch. | Adopted. | The repository extends ERPNext/Frappe instead of rebuilding accounting, stock, tax, permissions, workflow, and audit primitives. |
| Build an AI-native vertical ERP first. | Adopted. | The first implemented pack is service operations; future packs stay behind design gates and manifest checks. |
| Start with professional-services/project-based ERP for speed. | Adjusted. | Service operations is still a project-and-service workflow, but adds parts, technician assignment, stock issue, closeout, manager review, and invoice readiness. That makes the demo more ERP-specific while staying small. |
| Architect so manufacturing can become vertical #2. | Adopted as roadmap intent. | Manufacturing is reserved as a future industry pack and must reuse ERPNext BOM, work order, stock, selling, and accounting capabilities before custom code is added. |
| Use a greenfield FastAPI backend with SQLAlchemy, PostgreSQL row-level tenancy, custom ledger, Next.js frontend, and app-owned ERP modules. | Rejected for MVP. | It would make the MVP spend effort on base ERP correctness instead of the differentiating industry and AI workflow. |
| Use ERPNext/Frappe if trustworthy accounting matters on day one. | Adopted. | ERPNext/Frappe is the system of record; custom behavior lives only in `apps/`, and AI provider logic lives in `services/ai_control_plane/`. |
| Keep the MVP modular-monolith before microservices. | Adopted. | The repo uses Frappe apps plus one small AI service boundary; new services require an ADR. |
| Use Docker Compose for self-hostable demo setup. | Adopted. | `infra/compose/docker-compose.dev.yml`, `development/README.md`, and `scripts/dev.sh` define the local stack. |
| Add RAG, agent runtime, typed tools, approvals, and audit logs. | Partially adopted. | The MVP implements draft-only AI proposals with citations and immutable review. Full RAG and broader agent runtime remain later work after safety and data-boundary tests exist. |
| Let agents execute high-value workflows such as overdue-invoice chasing, reconciliation, purchasing, reporting, and document intake. | Deferred and constrained. | These are valid roadmap candidates, but any customer message, money, stock, payroll, permission, or compliance mutation must go through deterministic ERP validation and an authorized approval. |
| Use AGPL-3.0 for open-core/SaaS protection. | Adopted as `AGPL-3.0-only`. | The network-source obligation fits a hosted AI ERP and is compatible with the GPLv3 ERPNext boundary; ADR-0005 records the decision. |
| Prepare a GitHub launch kit with README, one-command demo, CI, labels, contribution docs, and good-first issues. | Adopted as publication readiness work. | The repo contains CI, community files, issue templates, metadata manifests, quality gates, and a publication runbook. Release mode remains blocked until owner decisions and local cleanup are complete. |

## Blueprint insights retained for later phases

- Use a domain expert/accountant before expanding financial workflows.
- Treat EU data residency, GDPR, and AI auditability as product requirements
  before hosting real client data.
- Add SSO/SAML, advanced RBAC, hosted billing, and production observability only
  when the product moves from demo/self-host to managed SaaS.
- Keep manufacturing, distribution, maintenance/assets, and professional
  services as separate industry-pack candidates rather than a generic feature
  pile.

## Blueprint recommendations intentionally not implemented now

- A custom double-entry ledger.
- Shared-row PostgreSQL tenancy.
- A separate Next.js ERP frontend.
- Kubernetes, Helm, Terraform, or hosted SaaS billing.
- Autonomous customer messaging, autonomous posting, or automatic stock/finance
  changes.
- Any license change that is not reconciled across the root, apps, service,
  contribution policy, and package metadata.
