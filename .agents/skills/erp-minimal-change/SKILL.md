---
name: erp-minimal-change
description: Choose the smallest correct implementation for the AI ERP Demo. Use when adding, refactoring, fixing, reviewing code, selecting dependencies, or deciding whether a proposed ERP feature should exist at all.
---

# ERP Minimal Change

Apply this decision ladder only after reading the affected code and tracing the
business flow. Stop at the first option that safely satisfies the requirement.

1. Remove or defer speculative work that has no verified user or business need.
2. Reuse an existing project or Frappe/ERPNext capability.
3. Use the language standard library or database constraint.
4. Use a native platform capability.
5. Use an already approved dependency.
6. Write the smallest coherent implementation.

## Boundaries

- Fix the shared root cause rather than patching an individual symptom.
- Do not add abstractions, configuration, services, or dependencies for an
  unproven future requirement.
- Prefer deletion and explicit, boring code over clever infrastructure.
- Leave a focused runnable check for non-trivial logic.

## Never simplify away

- Financial, tax, payroll, inventory, identity, tenant-isolation, or
  authorization correctness.
- Approval flows, audit records, contract compatibility, validation at trust
  boundaries, recovery behavior, security, or accessibility.
- Required Frappe upgrade boundaries, ADRs, integration idempotency, or the
  project quality gates.

When the smallest implementation has a known ceiling, record it with a
`ponytail:` comment and name the upgrade trigger.

Derived from the minimal-change principles of Ponytail v4.8.4 (MIT). No
Ponytail hooks, MCP server, benchmarks, or runtime dependencies are included.
