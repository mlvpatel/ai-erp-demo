# MVP threat model

- Scope: local AI ERP Demo repository, Frappe/ERPNext site, custom apps, AI
  control plane, and future connector boundaries.
- Status: MVP baseline.
- Review date: 2026-07-10.

## Assets to protect

- Customer, contact, service-location, employee, supplier, and user records.
- Financial records, invoices, taxes, stock ledger, payroll, roles, and
  permission state.
- AI proposal inputs, outputs, prompt versions, citations, review decisions,
  and source hashes.
- API secrets, model keys, database credentials, session cookies, backups, and
  private prompts.
- Tenant/site separation and audit history.

## Trust boundaries

```text
Browser / user session
        |
        v
Frappe site and ERPNext permissions
        |
        +--> Custom Frappe apps
        |      - ai_erp_core
        |      - ai_erp_service
        |      - future industry packs
        |
        +--> Approved API boundary
                |
                v
        AI control plane
                |
                +--> allow-listed OpenAI provider adapter
                +--> future retrieval/tool adapter
```

All transaction-authoritative state stays inside the Frappe/ERPNext site.
The AI control plane is allowed to draft, classify, summarize, retrieve, and
propose. It is not allowed to directly post financial, inventory, payroll,
permission, or compliance changes.

## High-priority threats

| Threat | Example | Required control |
| --- | --- | --- |
| Unauthorized ERP mutation by AI | A model response causes a submitted invoice, stock entry, payroll change, or role change. | The [`ai-control-plane-v1`](../../contracts/openapi/ai-control-plane-v1.yaml) contract returns proposals only; Frappe role checks and deterministic workflow code perform any transaction. |
| Tenant boundary leak | A user or AI request sees records from another Frappe site. | One site/database per tenant for MVP; do not share local site data across requests. |
| Role bypass | A technician closes work, issues parts, or drafts an invoice without manager authority. | Enforce Frappe permissions and explicit role checks in server-side methods. |
| Duplicate transaction | Retrying a button creates multiple Stock Entries, Sales Invoices, or external writes. | Lock the source document, store target IDs, and make writes idempotent. |
| Prompt/data leakage | Customer contacts, addresses, credentials, attachments, or private prompts are sent to a model unnecessarily. | Use allow-listed fields, source hashes, and no attachment contents in the first AI workflow. |
| Provider residency or retention mismatch | Operational notes are processed outside the approved region or retained under an unapproved policy. | Production OpenAI calls use the allow-listed EU origin only after DPA/DPIA, European data-residency, and retention/abuse-monitoring approval; synthetic data remains the default. |
| Prompt injection in work-order text | A note tells the model to ignore policy, reveal data, or claim an ERP action. | Treat every source field as untrusted data, use strict one-field structured output with no tools, and construct policy/citations locally. |
| Provider cost or worker exhaustion | Oversized records or slow calls consume tokens and synchronous workers. | Contract-level size/count limits, pinned model/output budget, bounded timeout, and no automatic retries; production capacity tests set concurrency limits. |
| Secret exposure in GitHub | `.env`, keys, database dumps, or production exports are committed or pasted into issues. | Keep `.gitignore`, publication runbook, and issue templates explicit; use synthetic fixtures only. |
| Sensitive telemetry leak | Logs, metrics, traces, alert payloads, or dashboard screenshots expose customer data, prompt bodies, provider responses, or secrets. | Observability guidance must keep logs, metrics, and traces free of customer data, prompt bodies, and secrets. Production SIEM routing remains deployment-specific. |
| Unreviewed connector action | Future provider webhook or sync writes unsafe ERP state. | Treat [`service-operations-v1`](../../contracts/events/service-operations-v1.yaml) as notification-only; validate signatures where applicable, store sync state, and surface failures as reviewable ERP records. |
| Audit tampering | AI proposal or transaction evidence can be changed after approval. | Store immutable proposal records and link deterministic ERP records by ID. |

## Controls already expected in the MVP

- Frappe/ERPNext remains the transaction system of record.
- Tenant identity stays at the Frappe site and API edge; application code does
  not add a shared-row tenant identifier for the MVP.
- Upstream Frappe/ERPNext source is not patched or vendored.
- `ai_erp_core` stores immutable AI Proposal records with source hashes and
  human review status.
- `ai_erp_service` keeps stock issue and draft invoice creation manager-gated
  and idempotent.
- The AI closeout draft sends only allow-listed service-work-order fields and
  has no ERP side effect on approval.
- The OpenAI adapter additionally removes tenant, requester, record, source,
  technician, and warehouse identifiers; it sends no tools and uses
  `store=false` with strict structured output.
- Audit evidence stays reviewable through AI Proposal source hashes, reviewer
  metadata, and deterministic Stock Entry or Sales Invoice identifiers linked
  back to the Service Work Order.
- Docker development images and upstream commits are pinned in tracked defaults.

## Required review questions for every feature

1. Which ERP record is the system of record?
2. Which role can create, update, approve, and reverse the action?
3. Can a retry duplicate money, stock, payroll, access, or external writes?
4. What exact data leaves the Frappe site?
5. Can the AI output change business state directly?
6. What audit record proves who requested, approved, and executed the action?
7. What test proves unauthorized users are blocked?

## Production controls still requiring deployment evidence

These are launch gates, not claims made by the repository:

- Live TLS, WAF, backups, restore evidence, key rotation, and SIEM routing.
  Production SIEM routing remains deployment-specific.
- Formal SOC 2, HIPAA, GDPR, or tax-compliance certification.
- Cross-tenant shared-row tenancy.
- Legal approval of the provider DPA/DPIA, retention, subprocessors, and
  international-transfer position.

See [ADR-0006](../adr/0006-openai-responses-provider-for-draft-summaries.md)
for the provider boundary. OpenAI documents the Responses API, model snapshots,
and data controls at:

- <https://developers.openai.com/api/reference/responses/create>
- <https://developers.openai.com/api/docs/models/gpt-5.4-mini>
- <https://platform.openai.com/docs/models/default-usage-policies-by-endpoint>
