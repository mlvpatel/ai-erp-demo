# Production-pilot remediation status — 2026-07-15

This record separates checked-in engineering controls from evidence that can
only be produced in a protected deployment or by accountable humans.

## Implemented in the candidate branch

- Field-service technician access is assignment-scoped. Manager-controlled and
  finance-controlled fields have separate permission levels plus server-side
  immutable-field validation. Technician sharing, emailing, billing-rate edits,
  direct invoicing, unrelated-record reads, and profitability access have
  negative tests.
- One scheduled overdue `Cannot Close` escalation notifies managers and never
  auto-closes a work order.
- The OpenAI adapter validates bounded typed requests, redacts high-confidence
  identifiers and secrets, uses an eight-second provider timeout and zero
  retries, validates returned provider/model metadata, limits requests per site,
  serializes proposals by work order, and exposes separate liveness/readiness.
- Production delivery is split into protected plan, inactive foundation,
  activation, and rollback operations. Terraform has typed replacement policy,
  workload-separated security groups, database TLS, isolated recovery state,
  expanded alarms, and no blanket PowerUserAccess deployment role.
- Production images are built before promotion, scanned for unresolved
  HIGH/CRITICAL findings and secrets, attested with SBOM/provenance, signed, and
  deployed by digest.
- Distribution and light manufacturing remain synthetic `configured_demo`
  workflows using standard ERPNext records. Automated integration evidence
  constructs their downstream draft handoffs and rolls the transaction back.
- Playwright covers visible forms and actions for Technician, Dispatcher,
  Service Manager, Accounts User, and AI Approver, plus mobile, keyboard,
  validation, attachment, unauthorized-control, and configured-demo checks.

## Evidence still required before pilot approval

- A clean-clone or clean-export publication validation for the exact release
  commit and green protected GitHub checks.
- Reviewed AWS cost estimate, account/OIDC, domain/certificate, secret values,
  protected foundation and activation runs, and authenticated production smoke.
- Private live OpenAI evaluation with approved synthetic/redacted cases and
  spend/rate evidence.
- Exact full-capacity profile and ten-request/five-user concurrency evidence on
  authorized disposable infrastructure.
- Backup, isolated restore, deletion, service-recovery, and compatible rollback
  drills meeting the documented RPO/RTO checklist.
- Human UAT, design-partner validation, legal/DPA/DPIA review, named support and
  on-call ownership, and accountable go/no-go.

The repository must keep `automated_complete`,
`deployment_evidence_complete`, and `pilot_approved` false until their distinct
evidence exists. Local synthetic success is not production approval.
