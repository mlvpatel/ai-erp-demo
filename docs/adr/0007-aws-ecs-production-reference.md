# ADR-0007: Use ECS Fargate for the first AWS production reference

- Status: Accepted for plan and validation; apply requires owner approval
- Date: 2026-07-14
- Region: `eu-central-1`
- Owners: AI ERP Demo

## Context

The repository has a reproducible development stack but no production hosting
topology. The first deployment targets a small service-operations pilot in the
EU. It needs isolated tenants, TLS, secrets, monitoring, backups, and controlled
release/rollback without introducing Kubernetes operations before they are
justified.

## Decision

Use Amazon ECS on Fargate for separately scalable Frappe web, websocket,
scheduler, short-worker, and long-worker services plus a private AI control
plane. Use an internet-facing ALB with ACM TLS and WAF only for Frappe; the AI
control plane has no public listener. Tasks run in private subnets without
public IPs. Images are built once, scanned, addressed by digest in ECR, and
promoted through a protected GitHub environment using OIDC rather than static
AWS keys.

Use one Frappe site and database per tenant. Use RDS MariaDB Multi-AZ for the
transactional database, ElastiCache for Redis runtime roles, encrypted EFS for
the minimum shared site files requiring POSIX semantics, and versioned SSE-KMS
S3 for site-scoped logical backups. RDS point-in-time recovery complements but
does not replace logical Frappe backups and tenant-level restore drills.

Use Secrets Manager with a customer-managed KMS key for database, Frappe,
control-plane, and OpenAI credentials. Secret values are inputs to the secret
store outside Terraform and must never enter variables, state, plans, logs, or
Git. Rotation requires a new ECS deployment because injected environment
secrets are read at task start.

CloudWatch receives redacted application logs, metrics, dashboards, and alarms;
CloudTrail records AWS control-plane activity. Default-deny security groups,
VPC endpoints where cost-approved, WAF rate limits, health checks, deployment
circuit breakers, minimum healthy capacity, and explicit resource quotas are
required.

## Apply gate

No billable resource may be created until the owner approves:

- AWS account and numeric monthly budget with alert thresholds,
- domain and DNS ownership,
- pilot tenant and data classification,
- RPO, RTO, backup retention, and deletion policy,
- production support/on-call owner,
- DPA/DPIA and EU OpenAI residency/retention eligibility,
- a Terraform plan and estimated recurring cost.

## Consequences

- ECS has less operational surface than EKS for the current team and scale.
- EFS and multiple Fargate services add cost but preserve the Frappe process
  topology and shared file behavior.
- Per-site/database isolation makes tenant restore and deletion clearer but
  requires tenant provisioning/decommission automation.
- A future move to EKS, shared-row tenancy, or another region needs a new ADR.

## Sources

- AWS Fargate task requirements and supported storage:
  <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html>
- ECS Secrets Manager injection and restart-on-rotation behavior:
  <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/secrets-envvar-secrets-manager.html>
- RDS Multi-AZ backup and point-in-time restore:
  <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/multi-az-db-clusters-concepts.html>

