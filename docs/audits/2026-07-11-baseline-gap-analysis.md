# Historical baseline audit — 2026-07-11

> [!CAUTION]
> This is a sanitized historical snapshot, not a statement of current product
> readiness. Repository-relative references replace the source report's local
> workstation links, and the remediation status supersedes claims that changed.

## Provenance

- Source title: `AI ERP Demo — Full Audit & Gap Analysis`
- Source date: 2026-07-11
- Source SHA-256:
  `ad6d666cf119ab84bde74332e643eb7a1fdab56b06aaca7ca4aec6152a03a400`
- Current disposition: [`2026-07-12-remediation-status.md`](2026-07-12-remediation-status.md)

The source audit was read-only. This archive preserves its findings and
severity labels while excluding absolute paths, private contacts, local
credentials, and unrelated customer-project identifiers.

## Original assessment

The audit described the repository as an AI-assisted ERP product scaffold on
Frappe/ERPNext v16, with a separately governed FastAPI control plane and a
service-operations industry pack. It rated architecture and documentation
highly, considered security and code quality generally strong, and classified
testing, operations, licensing, and publication readiness as incomplete.

The source report specifically praised:

- the upstream-only Frappe/ERPNext extension model;
- the AI-proposes/ERP-validates boundary in ADR-0003 and ADR-0004;
- modular industry packs and versioned contracts;
- the Service Work Order state machine and idempotent transaction actions;
- immutable, reviewable AI Proposal records;
- strict response validation, content hashes, and allow-listed AI context;
- extensive ADRs, runbooks, policy manifests, and repository gates.

## Architecture findings

| ID | Original severity | Historical finding |
| --- | --- | --- |
| A1 | Medium | Only the deterministic `template` provider existed; a real model adapter remained a product decision. |
| A2 | Low | `apps/ai_erp_connectors/` was a placeholder rather than an implemented connector app. |
| A3 | Low | Event contracts were intentionally `contract-only`; no producer published them. |
| A4 | Low | Distribution and manufacturing industry packs were documented placeholders. |

## Code-quality findings

| ID | Original severity | Historical finding |
| --- | --- | --- |
| C1 | High | The audit incorrectly inferred that local `development/.env` was tracked and contained weak placeholders. Git evidence later disproved the tracked-file claim. |
| C2 | Medium | The local environment copy differed from digest-pinned example values; the work order later prohibited changing this ignored local file. |
| C3 | Low | Local Python cache directories existed even though ignore rules excluded them. |
| C4 | Low | Generated Frappe hook files contained substantial boilerplate comments. |
| C5 | Medium | Proposal insertion used `ignore_permissions=True` behind the validated control-plane boundary and warranted explicit security review. |
| C6 | Medium | Closure-exception writes used `ignore_permissions=True` after role and workflow validation. |
| C7 | Low | The proposal bridge returned a deliberately generic error for broad request failures while logging details. |
| C8 | Medium | CI selected Python 3.14; the audit questioned ecosystem availability at that date. The pushed CI later proved the runtime available. |

## Security findings

| ID | Original severity | Historical finding |
| --- | --- | --- |
| S1 | High | Duplicate of C1: the audit believed a local environment file was tracked; later Git verification disproved it. |
| S2 | Medium | The local control plane had no rate limiter. |
| S3 | Medium | Local Compose traffic between Frappe and the control plane used plain HTTP. |
| S4 | Medium | The local service boundary used one static bearer secret without production rotation or request signing. |
| S5 | Low | Frappe supplied CSRF protection for session calls, while token callers depended on normal API authentication controls. |
| S6 | Medium | Permission-query hooks used escaped SQL interpolation following Frappe's supported pattern. |

The audit also verified the core AI safety properties: no database credentials
in the control plane, `draft_only` policy, `allowed_action: none`, forbidden
extra model fields, PII-free event payloads, and no direct ERP side effect from
AI proposal review.

## Test findings

| ID | Original severity | Historical finding |
| --- | --- | --- |
| T1 | Medium | No browser end-to-end suite existed. |
| T2 | Low | Performance artifacts were planning-only and had no runner. |
| T3 | Low | Shared test fixtures were placeholders; integration tests created data inline. |
| T4 | Medium | `ai_erp_core` lacked dedicated AI Proposal permission tests. |
| T5 | Medium | The control plane lacked direct HTTP security tests. |
| T6 | Low | Several role-bearing DocTypes lacked dedicated negative authorization tests. |
| T7 | Low | AI draft source-field coverage did not assert every expected field. |

The baseline inventory identified integration tests for service work orders,
OpenAPI contract tests, event contract tests, and more than 30 policy/quality
gate scripts. Line counts in the original report were point-in-time observations
and are intentionally omitted here.

## Documentation findings

| ID | Original severity | Historical finding |
| --- | --- | --- |
| D1 | Blocker | No root license had been selected. The owner later selected `AGPL-3.0-only` before private publication. |
| D2 | Medium | Per-app license metadata still contained placeholder identity fields. |
| D3 | Low | App metadata used a placeholder contact address. |
| D4 | Low | Public demo screenshots or a GIF were not yet included. |
| D5 | Low | Contracts existed without a separately rendered integrator API guide. |

The audit rated the ADRs, architecture documentation, product traceability,
security guidance, operational runbooks, community files, and machine-readable
policy manifests as unusually complete for an MVP.

## Infrastructure findings

| ID | Original severity | Historical finding |
| --- | --- | --- |
| I1 | Low | `infra/kubernetes/` was intentionally reserved and empty. |
| I2 | Medium | Observability assets were initially placeholders. |
| I3 | Medium | `infra/security/` was reserved and empty; design guidance lived under `docs/security/`. |
| I4 | Medium | Backup and restore procedures were not yet documented. |
| I5 | Medium | CI had not yet run on a real GitHub repository. |
| I6 | Low | Only a development Compose topology existed. |

## Original priority groups

### Publication blockers

The source report called for an owner-selected license, proof that local
environment files were untracked, Git initialization and history scanning,
replacement of public metadata placeholders, real CI execution, and release
readiness checks. The current remediation status records which of those claims
were corrected, implemented, or superseded.

### Alpha priorities

The report proposed dedicated AI Proposal tests, control-plane endpoint tests,
a browser smoke test, reproducible local configuration, rate limiting, an
approved model-adapter design, observable logging, and visual demo material.

### Production priorities

The report deferred TLS, secret rotation, backup automation, broader security
scanning, negative authorization tests, event publishing, load testing, and a
review of permission-bypassing writes to production-readiness work.

## Historical conclusion

The audit considered the design and governance unusually strong for an MVP but
explicitly rejected a production-readiness claim. That conclusion remains a
historical assessment only. Use the remediation status, current tests, release
manifest, and live repository settings for present-state decisions.
