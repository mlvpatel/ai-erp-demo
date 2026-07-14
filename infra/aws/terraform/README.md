# AWS production pilot foundation

This flat Terraform root codifies the plan-only foundation accepted by ADR-0007
for `eu-central-1`. It creates no resources unless an authorized operator runs
`terraform apply`. Repository scripts and CI never run apply or configure AWS
credentials.

The foundation covers two-AZ networking, an HTTPS ALB and WAF, an encrypted ECS
cluster, RDS MariaDB Multi-AZ with an AWS-managed master secret, encrypted
ElastiCache, encrypted EFS, a versioned SSE-KMS backup bucket, empty Secrets
Manager containers, CloudWatch alarms, and a numeric USD budget.

It intentionally has no ECS task definitions or services. Production Frappe and
AI images, commands, CPU/memory sizing, secret schemas, autoscaling limits, and
database/Redis client TLS settings require a separately reviewed workload
slice. The development `sleep infinity` image is not a production artifact.

## Credential-free validation

Use Terraform 1.13.5 and AWS provider 6.51.0:

```sh
python3 scripts/check-aws-iac.py
terraform -chdir=infra/aws/terraform fmt -check -recursive
terraform -chdir=infra/aws/terraform init -backend=false
terraform -chdir=infra/aws/terraform validate
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

Secret resources contain metadata only. Seed their values out-of-band after
approval. Never add `aws_secretsmanager_secret_version`, plaintext secret
variables, or `random_password`; those values would enter Terraform state.
