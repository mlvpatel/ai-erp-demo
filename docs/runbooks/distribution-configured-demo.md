# Distribution configured demo

Status: synthetic standard-ERPNext walkthrough; human validation remains
pending. This is not an implemented industry app or production workflow.

## Safety preconditions

- Use only the local `ai-erp.localhost` site and synthetic data.
- Run setup/reset as a System Manager. Use separate standard ERPNext Sales and
  Stock roles for the manual steps.
- Record the Stock Ledger Entry and GL Entry counts before the walkthrough.
- Do not enable negative stock or grant broader roles to make the demo pass.

## Reset and seed

Run inside the Frappe container or Bench environment:

```sh
AI_ERP_CONFIGURED_DEMO_ALLOW=1 bench --site ai-erp.localhost execute \
  ai_erp_core.configured_demo.reset --kwargs '{"pack":"distribution"}'
AI_ERP_CONFIGURED_DEMO_ALLOW=1 bench --site ai-erp.localhost execute \
  ai_erp_core.configured_demo.seed --kwargs '{"pack":"distribution"}'
```

Reset is idempotent but fail-closed: it will not cancel or delete submitted
records. After a walkthrough, an authorized user must cancel/delete linked
Delivery Notes, Pick Lists, and the Sales Order in reverse order before reset.
Reset retains any configured-demo warehouse that contains stock; an authorized
stock workflow must empty it before removal.

## Walkthrough

1. Confirm the result names two warehouses, two stock items, one customer, and
   one draft Sales Order. Both items deliberately have zero available stock.
2. As a Sales User, open the draft Sales Order and confirm quantities and the
   source warehouse. The user cannot post stock.
3. As a Sales Manager, review and manually submit the Sales Order.
4. As a Stock User, use the standard **Create → Pick List** action. Confirm the
   shortage from native Bin/availability data and keep the Pick List draft.
5. As a Distribution/Stock Manager, choose a human resolution: replenish,
   reduce/partially fulfill, backorder, or stop. Do not use AI to choose.
6. After an authorized resolution, use standard ERPNext to create the Delivery
   Note handoff. Save it as draft; a separately authorized stock user decides
   whether to submit it.

## Expected results

- The initial Sales Order, Pick List, and Delivery Note handoff are human-owned
  standard ERPNext records.
- Shortage is visible without a custom DocType, custom industry app, or AI
  route.
- Seeding changes neither Stock Ledger Entry nor GL Entry counts and creates no
  submitted transaction.
- Unauthorized roles cannot submit sales, stock, or delivery records.
- Re-running seed returns the same draft record names and creates no duplicate.

Verify with the manifest at `config/industry-demo-distribution.json` and the
focused `ai_erp_core.tests.test_configured_demo` suite.
