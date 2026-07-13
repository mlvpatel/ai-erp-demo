# Historical remediation work order — 2026-07-12

> [!CAUTION]
> This is a sanitized archive of the task specification. It is not current
> execution evidence. Later owner decisions, commits, tests, and the remediation
> status control when they conflict with this snapshot.

## Provenance

- Source title: `ERP demo — audit remediation work order (for Codex)`
- Source date: 2026-07-12
- Source SHA-256:
  `058d1f45cb6bd772f55c0c43d2157aaaaa9826d0c28ea9adc8de97c0a5002995`
- Current disposition: [`2026-07-12-remediation-status.md`](2026-07-12-remediation-status.md)

The source contained no customer data, but this repository copy omits its
external pathname and normalizes all references to repository-relative form.

## Operating constraints

The work order required one independently shippable concern per commit, the
smallest change satisfying acceptance, and green static, contract, and
control-plane checks after every task. It prohibited vendoring upstream
Frappe/ERPNext, touching the ignored Bench checkout, publishing secrets or real
customer data, and weakening the draft-only AI boundary.

The following items were declared intentional and outside remediation scope:

- `service-operations-v1` remained `contract-only`;
- `infra/kubernetes/` remained reserved and empty;
- manual release-readiness gates remained manual;
- ignored `development/.env` remained local-only;
- the single proposal action remained the documented MVP scope;
- no model-provider adapter could be selected without an owner product decision.

The source also prohibited selecting a license because that decision was still
open on 2026-07-12. The owner subsequently chose `AGPL-3.0-only`; that later,
explicit decision supersedes only this historical restriction.

## Task index

| Priority | Task | Finding | Required result | Recorded implementation |
| --- | --- | --- | --- | --- |
| P0 | T-01 | GOV-01 | Run Frappe behavioral tests in CI, or explicitly label the fallback as anchor verification. | `fa19896` uses the documented fallback. |
| P0 | T-02 | PERF-01/02 | Add a performance runner or consistently label the layer planning-only. | `2729151` selects planning-only. |
| P1 | T-03 | AIP-01 | Test missing, invalid, and valid service authentication plus provider-unavailable behavior. | `bfb8a99` |
| P1 | T-04 | AIP-02 + INF-04 | Run the control-plane image as a non-root user without breaking health checks. | `3d82d43` |
| P1 | T-05 | CON-02 + CON-03 | Add `/healthz` and provider-unavailable responses to the OpenAPI contract. | `5028936` |
| P1 | T-06 | CON-04 | Make contract tests detect exact path and response drift. | `682f41a` |
| P1 | T-07 | SEC-02 | Account for `Service Request` in the authorization matrix. | `41a12e6` |
| P1 | T-08 | DOC-01 | Reconcile BACKLOG rows with first-public-issue entries. | `010473e` |
| P1 | T-09 | APP-02 | Test requester isolation through query and direct permission paths. | `81a68d3` |
| P1 | T-10 | PERF-03 | Replace the scaffold test and run the full service app test suite. | `e4588b1` |
| P1 | T-11 | INF-01 | Wire documented upstream commit overrides into Compose. | `8d88dfa` |
| P1 | T-12 | INF-03 | Add Redis health checks and service restart policies. | `b680c7b` |
| P1 | T-13 | ARCH-01 | Fail the structure gate on unexpected root entries. | `4a6eced` |
| P1 | T-14 | GOV-03 | Declare PyYAML for contract tests instead of relying on a transitive install. | `79929ac` |
| P1 | T-15 | GOV-02 | Add a green Ruff CI job and reconcile its policy documentation. | `5176840` |
| P2 | T-16 | APP-01 | Add a manager-gated Issue Parts UI action or document API-only behavior. | `feece53` adds the action. |
| P2 | T-17 | CON-05 | Remove cited Python caches only if tracked evidence reproduces. | Skipped: paths were ignored and untracked. |
| P2 | T-18 | SEC-03 | Refresh or remove the ignored local environment copy. | Blocked: the same work order explicitly prohibited touching it. |
| P2 | T-19 | PERF-04/GOV-04 | Explain manual release evidence and strict owner/license checks. | `627e1e2` |
| P2 | T-20 | PERF-06 | Label end-to-end and performance test layers as planned. | `2ff0504` |
| P2 | T-21 | ARCH-04 | Document the intentional single-action core MVP. | `ec4ea5e` |
| P2 | T-22 | ARCH-02 | Map `agents/` and `.agents/` responsibilities. | `e3ed9e6` |
| P2 | T-23 | ARCH-03 | Map separate Redis cache and queue services. | `f164971` |
| P2 | T-24 | INF-05 | Explain the reserved `infra/security/` directory. | `892bb49` |
| P2 | T-25 | INF-06 | Reuse the Compose validation helper in CI. | `a0aa1af` |
| P2 | T-26 | DOC-03 | Link the MVP container architecture from the docs index. | `248633e` |
| P2 | T-27 | DOC-04 | Normalize ADR-0002 to a documented status. | `d9045f9` |
| P2 | T-28 | CON-06 | Name the API and event contract IDs in threat controls. | `e9a7a87` |
| P2 | T-29 | INF-02R | Add an example Frappe latency alert and require it in policy. | `2da4238` |

## Acceptance themes

Task-specific acceptance required the relevant repository policy checks plus:

- exact OpenAPI drift detection for T-05 and T-06;
- role and tenant isolation for T-07 and T-09;
- full service-app coverage for T-10;
- reproducible Compose rendering for T-11, T-12, and T-25;
- negative structure-gate behavior for T-13;
- explicit dependency installation and contract execution for T-14;
- green Ruff execution for T-15;
- no source diff when T-17 evidence did not reproduce;
- no prohibited edit for T-18.

The source verification matrix named:

```text
scripts/run-quality-gates.sh
python -m unittest discover -s tests/contract -v
cd services/ai_control_plane && python -m unittest discover -s tests -v
scripts/dev.sh compose-config
scripts/dev.sh up && scripts/dev.sh bootstrap && scripts/dev.sh service-test
```

The full-stack path could use T-01's explicit documentation fallback when the
environment could not run Docker.

## Human decisions preserved

- SEC-01: choose a concrete private vulnerability-reporting channel.
- License: historical owner decision, later resolved as `AGPL-3.0-only`.
- AIP-03: choose whether and when to build a real provider adapter.

No provider choice is inferred by this archive, and the template provider must
continue to fail closed for unapproved values.
