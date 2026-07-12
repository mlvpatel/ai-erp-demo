# Authorization and approvals

ERP state changes must be authorized by Frappe roles and deterministic server
methods. AI output may support a decision, but it must not bypass role checks,
DocType permissions, or human approval.

## Role boundaries

| Role | Boundary |
| --- | --- |
| Service Dispatcher | Creates, schedules, and cancels service work. |
| Service Technician | Sees assigned Service Work Orders, records own time, declares parts, and submits closeout. |
| Service Manager | Closes work, issues declared parts, marks invoice-ready, and drafts linked Sales Invoices. |
| Service Closure Owner | Reviews owned Service Closure Exceptions. |
| AI Proposal Requester | Reads AI proposals they requested. |
| AI Proposal Approver | Approves or rejects AI proposals without changing ERP transaction state. |
| System Manager | Administrative override for setup and tests. |

## Sensitive actions

The MVP treats these actions as high risk:

- update execution status for a Service Work Order,
- close work or mark a work order invoice-ready,
- create a submitted ERPNext Material Issue,
- create a linked draft ERPNext Sales Invoice,
- request a closeout AI proposal,
- approve or reject an AI proposal.

Every high-risk action needs:

1. a server-side role check or Frappe permission check,
2. a deterministic validation path,
3. an idempotency or immutability guard when money, stock, or AI evidence is
   involved,
4. a negative test proving unauthorized users are blocked,
5. documentation in the service workflow or security docs.

## Approval rules

- Technicians may submit closeout only for assigned work.
- Managers or System Managers may close work, issue stock, mark invoice-ready,
  and draft linked Sales Invoices.
- Sales Invoice creation also requires standard ERPNext `Sales Invoice` create
  permission.
- AI Proposal approvers may record review decisions only.
- AI Proposal approval must not update closeout notes, status, invoices, stock,
  payroll, permissions, compliance state, or external communications.

The machine-readable authorization matrix is
`config/authorization-matrix.json`. The static quality gate runs
`scripts/check-authorization-matrix.py` so roles, permission hooks, sensitive
actions, tests, and docs stay aligned.
