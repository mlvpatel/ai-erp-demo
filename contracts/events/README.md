# Business event contracts

Business event contracts are versioned here before connector implementations
depend on them. The MVP does not publish asynchronous events yet; the current
catalog defines the safe payload shape future adapters must follow.

Rules:

- Emit identifiers and workflow facts, not customer contact details, addresses,
  attachment contents, credentials, private prompts, or ledger lines.
- Events are notifications. They do not grant permission to mutate ERP state.
- Consumers must fetch any additional ERP data through an authorized API using
  their own permissions.
- New event types require a contract update, a producer/consumer test, and a
  security review for tenant, role, audit, and idempotency boundaries.

Current catalog:

- `service-operations-v1.yaml`: service work-order and AI-review events for the
  first industry pack.
