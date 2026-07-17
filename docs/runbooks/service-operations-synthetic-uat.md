# Service-operations synthetic UAT rehearsal

- Human UAT: not performed
- Design-partner approval: pending
- Real data: prohibited
- Result class: engineering rehearsal, not business acceptance

Use a disposable local site and synthetic fixtures. Record only command, commit,
UTC time, pass/fail, and public-safe notes. Do not capture names, tenant IDs,
addresses, screenshots with data, raw logs, prompt bodies, tokens, or signatures.

| Scenario | Actor | Expected result | Automated reference | Human evidence still required |
| --- | --- | --- | --- | --- |
| Assigned work list | Technician | Sees assigned order; cannot discover unrelated work | `scripts/dev.sh e2e-test` | Technician confirms usable flow |
| Intake and scheduling | Dispatcher | Creates/assigns synthetic work under configured permissions | Service integration suite | Dispatcher validates real process |
| Closeout guard | Technician | Cannot close without required deterministic evidence | Service integration suite | Business owner approves required fields |
| Parts issue | Service Manager | Authorized action is idempotent and stock-validated | Service integration suite | Stock owner approves segregation |
| Invoice draft | Finance-separated role | Draft only; no AI submission or posting | Service integration suite | Owner chooses finance role mapping |
| AI closeout summary | AI approver | Cited, immutable draft; provider failure mutates nothing | Control-plane and service suites | Reviewer judges usefulness/accuracy |
| Profitability | Service Manager | Permission-scoped aggregate report | Browser/performance smoke | Finance validates calculation policy |
| Retry | Manager | Repeated action cannot duplicate stock/invoice state | Service integration suite | Incident owner rehearses recovery |
| Restore/tabletop | Operations | Clean restore preserves permissions and audit links | Backup runbook only | Timed deployment restore drill |

Rehearsal commands:

```sh
scripts/dev.sh service-test
scripts/dev.sh e2e-test
scripts/dev.sh performance-smoke
```

Browser and performance results are engineering evidence only. The performance
smoke status is not a capacity claim, and this document cannot be signed as UAT
until named users execute approved scripts in the approved pilot environment.
