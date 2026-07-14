# AWS production pilot foundation

This flat Terraform root codifies the plan-only foundation accepted by ADR-0007
for `eu-central-1`. It creates no resources unless an authorized operator runs
`terraform apply`. Repository scripts and CI never run apply or configure AWS
credentials.

The balanced-pilot profile is capped at USD 600/month. It uses one NAT gateway,
RDS MariaDB Multi-AZ with 14-day backups, one encrypted Valkey node, encrypted
EFS, versioned SSE-KMS S3 backups, an HTTPS ALB/WAF, and private ECS Fargate
services. The single NAT and single Valkey node are explicit cost/availability
tradeoffs; RDS remains Multi-AZ because transaction recovery is not simplified.

Workloads use immutable ECR digest inputs. Frappe web, websocket, scheduler,
short worker, long worker, and the private AI control plane have bounded sizing,
deployment circuit-breaker rollback, service-count alarms, and CPU target
tracking where horizontal scaling is safe. Scheduler remains a singleton.
`configure`, `migrate`, and `backup` are registered task definitions only;
Terraform never runs them. The development `sleep infinity` image is not a
production artifact.

## Credential-free validation

Use Terraform 1.13.5 and AWS provider 6.51.0:

```sh
python3 scripts/check-aws-iac.py
terraform -chdir=infra/aws/terraform fmt -check -recursive
terraform -chdir=infra/aws/terraform init -backend=false
terraform -chdir=infra/aws/terraform validate
bash -n infra/images/frappe/runtime.sh
```

`terraform validate` checks syntax and internal consistency; it does not prove
AWS account readiness, costs, runtime health, backup restoration, or compliance.

## Private planning and apply gate

Copy `terraform.tfvars.example` to an untracked file outside the repository.
Use a separately bootstrapped, encrypted and access-logged S3 backend with state
locking. Never commit a real backend config, tfvars, state, plan, account ID,
domain, notification address, or secret value.

Before even a private plan, approve every ADR-0007 gate: AWS account, numeric
budget, domain/certificate, tenant/data class, RPO/RTO and retention, support
owner, DPA/DPIA, and OpenAI EU controls. Store a saved plan only under `/tmp`,
review its estimated recurring cost and policy output, then delete it.

Applying this stack creates billable NAT gateways, ALB/WAF, RDS, ElastiCache,
EFS, CloudWatch, KMS, and related resources. No apply is authorized by this
README or by a green validation result.

Secret resources contain metadata only. Seed their JSON values out-of-band after
approval. Never add `aws_secretsmanager_secret_version`, plaintext secret
variables, or `random_password`; those values would enter Terraform state.

The control-plane secret must contain `shared_secret`; the OpenAI secret must
contain `api_key`. Task startup fails closed when either is absent. An approved
operator must run `configure` and `migrate` before services receive traffic.
The `backup` task writes a logical site backup to encrypted EFS; copying it to
the backup bucket and proving a clean-site restore remain manual gates.
