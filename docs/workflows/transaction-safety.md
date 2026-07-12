# Transaction safety

ERP transactions must be deterministic, idempotent, role-gated, and auditable.
AI output may support review, but it must not create or submit ERP records.

## MVP transaction invariants

- Parts issue is manager-triggered and creates at most one submitted ERPNext
  Material Issue for the currently unissued rows.
- Draft invoice creation is manager-triggered, idempotent, draft-only, and
  never updates stock.
- Billing fields, time rows, and part rows cannot change after a Sales Invoice
  is linked.
- Invoice readiness is blocked by open closure exceptions and by unissued parts.
- AI Proposal review records approval or rejection only; it has no invoice,
  stock, status, payroll, permission, compliance, or email side effect.
- Demo seed creates synthetic setup data and stays before transaction actions.

## Required implementation pattern

For every future money, stock, payroll, access-control, compliance, or external
write path:

1. Check Frappe permissions and project roles server-side.
2. Lock the source ERP record before checking whether work is already done.
3. Store the target ERP/external record identifier on the source record.
4. Return the existing target identifier on retry instead of duplicating work.
5. Keep source evidence immutable after a financial or stock transaction exists.
6. Add a negative test for unauthorized users.
7. Add an idempotency test for retries.
8. Add a side-effect test proving AI review cannot trigger the transaction.

The machine-readable transaction safety contract is
`config/transaction-safety.json`. The static quality gate runs
`scripts/check-transaction-safety.py` to keep code snippets, docs, and tests
aligned.
