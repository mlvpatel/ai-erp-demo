# System boundaries

This document is the first map to read when deciding where new work belongs.
The MVP is a Frappe/ERPNext-based modular monolith with a separately governed
AI control plane. ERPNext remains the transaction system of record.

## Container map

```mermaid
flowchart TB
    user["Office users, technicians, managers"]
    browser["Frappe/ERPNext web UI and REST API"]
    erp["ERPNext/Frappe site\none tenant per site/database"]
    erpnext["ERPNext standard modules\nCRM, Stock, Selling, Accounting, Projects"]
    core["ai_erp_core\nAI proposal ledger and shared policies"]
    service["ai_erp_service\nservice work orders, closeout, parts, invoice readiness"]
    connectors["ai_erp_connectors\nfuture replaceable adapters"]
    db["MariaDB site database\ntransaction-authoritative state"]
    redis_cache["redis-cache\nFrappe cache"]
    redis_queue["redis-queue\njob queue and realtime"]
    ai["AI control plane\nFastAPI, policy, prompt rendering, proposals"]
    contracts["contracts/\nOpenAPI and business events"]
    model["Future model/provider adapters"]

    user --> browser
    browser --> erp
    erp --> erpnext
    erp --> core
    erp --> service
    erp --> connectors
    erp --> db
    erp --> redis_cache
    erp --> redis_queue
    erp -- "approved, least-privilege request" --> ai
    ai -- "draft proposal with citations" --> erp
    ai --> contracts
    ai -. "future provider calls" .-> model
```

## Write authority

| Area | Owns | May create authoritative ERP transactions? |
| --- | --- | --- |
| ERPNext/Frappe | Customers, items, stock, invoices, accounting, users, roles, workflows, audit history | Yes, through Frappe permissions and deterministic server-side methods |
| `apps/ai_erp_core` | Shared AI governance records and reusable policy helpers | Only for its own audit/proposal records |
| `apps/ai_erp_service` | Service-operation workflow records and manager-triggered ERP handoffs | Yes, but only through explicit role checks, idempotency, and ERPNext documents |
| `services/ai_control_plane` | Prompt rendering, policy metadata, draft proposals, citations, future provider adapters | No. It returns proposals; it does not post money, stock, payroll, access, or compliance changes |
| `contracts/` | Versioned external API and business-event shapes | No |

## AI approval path

```mermaid
sequenceDiagram
    participant User as Technician or Manager
    participant ERP as Frappe/ERPNext site
    participant Core as ai_erp_core AI Proposal
    participant AI as AI control plane
    participant Manager as Authorized reviewer

    User->>ERP: Request draft closeout summary
    ERP->>ERP: Select allow-listed source fields
    ERP->>AI: Send least-privilege context
    AI-->>ERP: Return draft text and citations
    ERP->>Core: Store immutable AI Proposal
    Manager->>Core: Review or approve proposal
    Core-->>ERP: Record review decision only
    Note over Core,ERP: Approval has no invoice, stock, payroll, role, compliance, or email side effect
```

## Service workflow path

```mermaid
flowchart LR
    request["Service Request"]
    work["Service Work Order"]
    schedule["Scheduled and assigned"]
    progress["Technician in progress"]
    closeout["Structured closeout\nor tracked exception"]
    stock["Manager issues parts\nidempotent Material Issue"]
    ready["Invoice Ready"]
    invoice["Manager drafts one linked\nERPNext Sales Invoice"]
    ai["Optional AI closeout draft\nreview-only"]

    request --> work --> schedule --> progress --> closeout --> stock --> ready --> invoice
    closeout -. "draft summary request" .-> ai
```

## Placement rule

- Reuse ERPNext/Frappe configuration before adding code.
- Put cross-industry behavior in `apps/ai_erp_core/`.
- Put first-vertical service behavior in `apps/ai_erp_service/`.
- Put provider calls, prompts, retrieval, and AI evaluations in
  `services/ai_control_plane/`.
- Put public schemas in `contracts/` before or with integration work.
- Put business-event schemas in `contracts/events/`; event payloads notify
  consumers and do not authorize ERP mutations.
- Keep tenant identity at the Frappe site and API edge. Do not add app-level
  shared-row tenant shortcuts for the MVP.
- Write an ADR before introducing a new service, datastore, external provider,
  or irreversible architectural dependency.

If a proposed feature bypasses this map, stop and update the ADRs before code.
