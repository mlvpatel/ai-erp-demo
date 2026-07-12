# ADR-0003: AI proposes; deterministic ERP workflows validate and approve

- Status: Accepted
- Date: 2026-07-10
- Owners: AI ERP Demo

## Context

AI workflows are a product differentiator, but an autonomous model must not
bypass financial, inventory, payroll, access-control, or compliance controls.

## Decision

Keep model routing, retrieval, prompts, tool orchestration, and evaluations in
`services/ai_control_plane`. The control plane may call explicitly approved ERP
tools, but it cannot write directly to the ERP database.

Consequential actions create a proposed action with source references, typed
parameters, policy result, approver, and outcome. The ERP workflow validates
and authorizes the action before it changes business state.

## Consequences

- The first AI feature can safely draft an overdue-invoice reminder or a work
  order closeout summary.
- Direct agent posting of journals, stock movements, payroll, or permissions is
  prohibited.
- Audit records and evaluations are required before agent actions are exposed
  to customers.

## Alternatives considered

- Model code writes directly to ERP tables: rejected because it bypasses
  controls and creates an unauditable shadow path.
