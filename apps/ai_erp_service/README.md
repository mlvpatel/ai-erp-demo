# AI ERP Service

The first AI ERP Demo industry pack: auditable service requests, field work
orders, technician closeout, controlled exceptions, and ERPNext-backed parts
issuance. It requires ERPNext v16.

## MVP workflow

This pack is the first implemented end-to-end demo workflow for AI ERP Demo.

`Service Request → Service Work Order → assigned technician → closeout → manager review → invoice-ready → draft Sales Invoice`

- Technicians can see only their assigned Service Work Orders, record their
  own time, attach closeout evidence, and submit a closeout or `Cannot Close`.
- `Cannot Close` requires a reason, named `exception_owner`, and due date; it
  creates or updates an owned Service Closure Exception.
- Only a Service Manager (or System Manager) can close a work order or mark it
  invoice-ready. Open exceptions block invoice readiness.
- A manager can issue declared parts only after closeout is submitted. The app
  creates a submitted ERPNext Material Issue and records the Stock Entry on
  each part row. It derives the company from the source warehouse, requires
  all issued parts to belong to one company, and locks the work order first so
  retries do not duplicate the issue.
- After invoice readiness, a manager with standard ERPNext Sales Invoice create
  permission can draft one linked ERPNext Sales Invoice. Labor is invoiced from
  the configured non-stock Labor Billing Item and Hourly Rate. Parts are
  invoiced from their Bill Rate after stock has already been issued. The action
  is idempotent, creates a draft only, does not submit the invoice, and does not
  update stock.
- The work order shows a read-only profitability projection. Revenue comes from
  labor and part bill rates. Parts cost comes from submitted ERPNext Stock Entry
  Detail amounts. The current projection is before labor overhead; employee
  costing is a future ERPNext Timesheet/HR integration.

## Governed AI closeout draft

After a closeout is submitted, the assigned technician or a Service Manager can
request a **Draft AI Closeout Summary**. The service app sends only the
allow-listed subject, description, closeout notes, typed time, and typed parts
to the stateless control plane. It never sends attachment contents, customer
contacts, addresses, credentials, or stock/accounting data.

This AI workflow is draft-only and requires human review before anyone uses the
text in an operational process.

The response is stored by `ai_erp_core` as an immutable, cited `AI Proposal`.
It records a request ID, input/output hashes, prompt/model metadata, source
hashes, requester, and human review decision. A user with the **AI Proposal
Approver** role may approve or reject it; users who need to view their own
drafts need **AI Proposal Requester**. A Service Manager should be assigned the
approver role as part of site setup.

Approval only records the decision. It cannot update closeout notes or work
order status, issue stock, create an invoice, send an email, change payroll, or
change access permissions. The AI control plane is intentionally outside this
app and cannot call the state-changing functions in this package.

The draft Sales Invoice action is separate from the AI closeout draft. It is a
human-triggered ERP action guarded by Frappe permissions and Service Manager
role checks; AI approval still has no invoice side effect.

## Local installation

This app is part of the AI ERP Demo monorepo. Use the root
`development/README.md` bootstrap flow; it links `apps/ai_erp_service` into the
local Frappe Bench checkout and installs it editable on the demo site.

If this industry pack is later split into a standalone Frappe app repository,
document that repository URL and branch here as part of the split.

## Development checks

From a Frappe Bench with the app installed:

```bash
bench --site ai-erp.localhost migrate
bench --site ai-erp.localhost set-config allow_tests true
bench --site ai-erp.localhost run-tests --app ai_erp_service \
  --doctype 'Service Work Order' --test-category integration --failfast
```

For a local synthetic demo record set, use the repository helper:

```bash
scripts/dev.sh seed-demo
```

## Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/ai_erp_service
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

## License

AGPL-3.0-only. See the repository root `LICENSE` file.
