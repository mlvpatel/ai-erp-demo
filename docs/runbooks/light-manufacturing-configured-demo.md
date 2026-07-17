# Light-manufacturing configured demo

Status: synthetic standard-ERPNext walkthrough; human validation remains
pending. This is not an implemented industry app or production workflow.

## Safety preconditions

- Use only the local `ai-erp.localhost` site and synthetic data.
- Run setup/reset as a System Manager. Separate Sales, Manufacturing, and Stock
  roles for the manual steps.
- Record the Stock Ledger Entry and GL Entry counts before the walkthrough.
- Do not enable negative stock, bypass BOM approval, or grant broader roles to
  make the demo pass.

## Reset and seed

Run inside the Frappe container or Bench environment:

```sh
AI_ERP_CONFIGURED_DEMO_ALLOW=1 bench --site ai-erp.localhost execute \
  ai_erp_core.configured_demo.reset --kwargs '{"pack":"light_manufacturing"}'
AI_ERP_CONFIGURED_DEMO_ALLOW=1 bench --site ai-erp.localhost execute \
  ai_erp_core.configured_demo.seed --kwargs '{"pack":"light_manufacturing"}'
```

Reset never cancels submitted records. After a walkthrough, authorized users
must cancel/delete Material Requests, Work Orders, Production Plans, the Sales
Order, and BOM in reverse dependency order before reset. Reset retains any
configured-demo warehouse that contains stock; an authorized stock workflow
must empty it before removal.

## Walkthrough

1. Confirm the result names raw-material, work-in-progress, and finished-goods
   warehouses; component/finished items; one draft BOM; and one draft Sales
   Order. Components deliberately have zero stock.
2. As Manufacturing Manager, review the BOM lines and manually submit the BOM.
3. As Sales Manager, review and manually submit the make-to-order Sales Order.
4. As Manufacturing User, create a standard Production Plan from the Sales
   Order, then create the draft Work Order through native ERPNext actions.
5. Inspect required items and native availability. The missing components are
   the deterministic shortage; no AI decides feasibility or releases work.
6. As the authorized planner, use the native shortage action or create a
   Material Request manually. Keep the Material Request draft for purchasing or
   transfer review.

## Expected results

- BOM approval, Production Plan, Work Order, and Material Request are explicit
  human ERPNext actions.
- Shortage is visible without a custom MRP engine, DocType, industry app, or AI
  route.
- Seeding changes neither Stock Ledger Entry nor GL Entry counts and creates no
  submitted transaction.
- Unauthorized roles cannot approve BOMs, release Work Orders, request
  material, or post stock.
- Re-running seed returns the same draft record names and creates no duplicate.

Verify with `config/industry-demo-light-manufacturing.json` and the focused
`ai_erp_core.tests.test_configured_demo` suite.
