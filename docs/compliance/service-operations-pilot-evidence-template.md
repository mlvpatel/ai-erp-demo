# Service-operations pilot evidence template

This public-safe index is neither GDPR compliance nor production approval.

- Human UAT: not performed
- Design-partner approval: pending
- Real data: prohibited

## Demo-state declaration

- Local/private synthetic demo: ready after repository gates pass.
- Required for demo: local/private dev stack and synthetic data only.
- Not required for demo: AWS apply, live OpenAI key, legal/DPA/DPIA approval,
  human UAT sign-off, restore drill, or pilot go/no-go.
- Production pilot remains blocked by the release-state gates below.

## Release-state declaration

- Automated complete: no; the repository gates must pass on the release commit.
- Deployment evidence complete: no; no credentialed AWS deployment has been approved.
- Human approval pending: yes.
- Pilot approved: no.

## Repository and synthetic evidence

| Evidence | Commit/config digest | Command | UTC timestamp | Result |
| --- | --- | --- | --- | --- |
| Static quality |  | `scripts/run-quality-gates.sh` |  |  |
| Service integration |  | `scripts/dev.sh service-test` |  |  |
| Browser role smoke |  | `scripts/dev.sh e2e-test` |  |  |
| Performance smoke |  | `scripts/dev.sh performance-smoke` |  |  |
| AI contract/control plane |  | documented contract commands |  |  |

## Private deployment evidence required

Keep account identifiers, domains, plan files, cost estimates, alarm routes,
restore artifacts, logs, screenshots, tenant mappings, and secret metadata in an
approved private evidence system. Record only a private evidence reference here
after access and retention are approved.

- Approved Terraform plan and cost review reference:
- TLS/WAF/secret/monitoring validation reference:
- Timed backup/restore and deletion-drill reference:
- Capacity/concurrency profile reference:
- Incident/on-call rehearsal reference:

## Human and legal approvals required

Do not store contracts, DPIAs, signatures, legal opinions, employee/customer
details, or identity documents in Git. Record only an approved reference and
decision date after review.

- Controller/processors, purposes, legal basis, and RoPA:
- DPA/subprocessor/transfer and DPIA/LIA decision:
- OpenAI EU data-control eligibility:
- Italian counsel or DPO review:
- Design-partner workflow validation:
- Role mapping and finance segregation:
- Human UAT signatures:
- Accountable owner pilot go/no-go:
