# Demo Version stack and AI integration

What this repository actually runs for the **Demo Version** local synthetic
product. Numbers and pins come from checked-in files, not marketing copy.

Related: [`demo-version-loop.md`](demo-version-loop.md),
[`tech-stack-2026-07.md`](../architecture/tech-stack-2026-07.md),
[`improvement-plan-unique-governed-secure.md`](improvement-plan-unique-governed-secure.md),
`config/demo-version.json`.

## Layers in use

| Layer | What is used | Where pinned / defined |
| --- | --- | --- |
| ERP core | ERPNext on Frappe, `version-16` branch, commit-pinned | `development/.env.example` (`FRAPPE_COMMIT`, `ERPNEXT_COMMIT`) |
| Local demo image tag | `frappe/erpnext:v16.26.2` for compose demo builds | `infra/compose/docker-compose.demo.yml` |
| Custom apps | `ai_erp_core`, `ai_erp_service` (distribution / manufacturing are configured demos only) | `apps/` |
| AI control plane | FastAPI service, Python `>=3.14`, httpx, PyYAML, uvicorn | `services/ai_control_plane/pyproject.toml` |
| Default AI provider | Deterministic `template` (zero cost) | `development/.env.example` (`AI_ERP_PROVIDER=template`) |
| Hosted provider path | OpenAI adapter with redaction, budgets, `store=false`; live eval gated | ADR-0006, `docs/runbooks/openai-live-evaluation.md` |
| Contracts | OpenAPI 3.1 control-plane + versioned service events | `contracts/openapi/`, `contracts/events/` |
| Data / queue | MariaDB + Redis (digest-pinned images) | `infra/compose/docker-compose.dev.yml` |
| Browser proof | Playwright `1.61.0` | `tests/e2e/package.json` |
| Gates | `scripts/run-quality-gates.sh` plus `scripts/dev.sh` suites | `docs/workflows/quality-gates.md` |
| Prod reference | Terraform for AWS ECS prepared; apply not authorized from this demo | `infra/aws/terraform/` |

## AI integration boundary

```text
Frappe Desk / ai_erp_service
        |  typed request over versioned OpenAPI
        v
AI control plane (stateless)
  - redaction and schema validation
  - template or pinned hosted adapter
  - returns draft-only proposal + citations
        |
        v
AI Proposal DocType (ai_erp_core)
  - immutable ledger, human review
  - approval does not post ERP transactions
```

Rules enforced in code and contracts:

- Policy block is constant `draft_only` with allowed action `none`.
- Control plane holds no ERP database credentials.
- Stock Entry and draft Sales Invoice stay deterministic Frappe methods under
  authorized roles.
- Raw prompts and provider response bodies stay out of Git, CI logs, and release
  evidence.

## What is demonstrated vs deferred

Demonstrated in Demo Version (synthetic, local):

- Service request → work order → schedule suggest → execute → evidence →
  margin risk → AI draft proposals → human review → invoice-ready → draft
  invoice → evidence replay/packet.
- Role separation (technician / manager / accounts / AI approver).
- Idempotent parts issue and draft invoice.
- Permission-scoped structured retrieval (not a vector store).

Deferred or blocked on credentials / humans:

- Live OpenAI evaluation aggregates.
- Design-partner scores, human UAT, counsel-signed DPA/DPIA, pilot go/no-go.
- AWS apply, full capacity, restore/rollback drills.
- Offline IndexedDB technician drafts (intentionally gated off).
- Distribution and manufacturing beyond `configured_demo`.

## Currency note

The July 2026 stack decision in `tech-stack-2026-07.md` remains the accepted
MVP direction. Runtime pins (Frappe/ERPNext commits, image digests, Playwright,
control-plane Python) may lag the absolute latest upstream tags by design;
upgrade only with `docs/workflows/upstream-upgrade-readiness.md` and passing
gates. Do not describe unpinned “latest everything” as what the demo runs.
