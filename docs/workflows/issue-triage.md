# Issue triage workflow

Use this workflow when turning backlog items, user requests, or public GitHub
issues into actionable work. The goal is to keep the project welcoming without
letting a small issue bypass ERP, tenant, or AI safety boundaries.

The label source of truth is `.github/labels.json`; keep this workflow,
`BACKLOG.md`, `config/first-public-issues.json`, and issue-template frontmatter
aligned with that manifest.

## Triage order

1. **Confirm licensing state.** Do not accept external public contributions
   until the root `LICENSE` and generated app metadata are reconciled.
2. **Classify the area.** Choose one primary area: docs, developer tooling,
   horizontal core, industry pack, AI workflow, contract, integration,
   infrastructure, security, or dependency update.
3. **Identify the business role.** Name the user role and business job. If the
   issue cannot name a business job, send it to discovery instead of design.
4. **Check the transaction boundary.** Flag any change that can create, submit,
   cancel, reverse, approve, hide, or notify from an ERP record.
5. **Check the AI boundary.** Flag any change that expands prompts, retrieval,
   model behavior, citations, tools, provider calls, or approval side effects.
6. **Require evidence.** Link the issue to a doc, interview note, existing
   workflow, failing test, contract mismatch, or reproducible local command.
7. **Set the smallest safe next action.** Prefer a discovery note, negative
   test, contract shape, or documentation improvement before transactional code.

## Routing table

| Issue shape | Route | Required labels | Minimum evidence before implementation |
| --- | --- | --- | --- |
| Typo, docs clarification, glossary, README improvement | Good first issue | `documentation`, `good first issue` | Link to affected doc and expected wording. |
| Local developer command, static check, or non-destructive helper | Good first issue if no secrets or cleanup risk | `developer tooling` | Command output before/after and no secret printing. |
| Service workflow field or state change | Maintainer review | `industry-pack`, `erp-safety` | Role/state table, permission impact, integration test plan. |
| Money, stock, payroll, permissions, compliance, tax, audit, or tenant scope | Maintainer review; never good first issue | `erp-safety` | ADR or design note, tests, rollback/recovery notes. |
| New or expanded AI workflow | AI workflow review | `ai-safety`, `discovery` | Completed AI workflow proposal template and security review. |
| OpenAPI or event schema change | Contract review | `contract` | Versioning decision and compatibility test plan. |
| New industry pack | Discovery first | `industry-pack`, `discovery` | Completed industry-pack proposal and design partner evidence. |
| Dependency, image, Frappe, or ERPNext pin change | Dependency workflow | `dependency` | `docs/workflows/dependency-updates.md` checklist and quality gates. |
| Potential vulnerability, secret, private data, or bypass | Security process | `security` | Follow `SECURITY.md`; avoid public sensitive details. |

## Safe first issue rules

A good first issue must satisfy all of these:

- It does not change financial, inventory, payroll, access-control,
  compliance, tenant isolation, or approval behavior.
- It does not add or modify model/provider calls, prompts, tools, or AI approval
  side effects.
- It can be verified with a local command or documentation review.
- It does not require real customer data, production logs, credentials, or
  private screenshots.
- It has clear acceptance criteria and a small file scope.

If any of these are false, remove `good first issue` and route the issue to a
maintainer review path.

Before creating the first public issues, run:

```sh
python3 scripts/check-first-public-issues.py
```

This validates that launch issues stay license-gated, use existing labels and
templates, link evidence, and avoid ERP/AI safety boundaries.

## Maintainer decision checklist

Before moving an issue from triage to implementation:

- [ ] The root license state allows the contribution type.
- [ ] The issue has one primary owner area.
- [ ] The issue names the business role and workflow.
- [ ] ERPNext/Frappe configuration was considered before custom code.
- [ ] The required docs are linked: architecture boundary, security review,
      contract, ADR, or discovery note as applicable.
- [ ] The test or quality-gate command is named before work starts.
- [ ] The acceptance criteria avoid broad "all industries" or autonomous AI
      claims unless implemented and verified.
