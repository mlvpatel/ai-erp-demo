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
`configure`, `migrate`, `backup`, `restore`, and the separate synthetic capacity
runner are registered task definitions only; Terraform never runs them. The development `sleep infinity` image is not a
production artifact.

Long-running ECS services default to zero tasks. Keep
`activate_services=false` for the foundation apply, seed the secret metadata,
run the configurator and migration task definitions successfully, and only then
apply the reviewed plan with `activate_services=true`. This prevents an empty
EFS mount from starting unhealthy services before the tenant site exists.

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

After the one-time bootstrap, `.github/workflows/production-deploy.yml` is the
only repository delivery path. It uses the protected `production` environment,
GitHub OIDC, encrypted S3 lockfiles, full-SHA-pinned actions, a reviewed monthly
cost input, and explicit apply or rollback confirmation. The apply path creates
the foundation with services inactive, verifies out-of-band secret keys, runs
the configurator and migration tasks, then activates services from a second
non-destructive plan. Rollback accepts only three prior reviewed image digests.

Applying this stack creates billable NAT gateways, ALB/WAF, RDS, ElastiCache,
EFS, CloudWatch, KMS, and related resources. No apply is authorized by this
README or by a green validation result.

Secret resources contain metadata only. Seed their JSON values out-of-band after
approval. Never add `aws_secretsmanager_secret_version`, plaintext secret
variables, or `random_password`; those values would enter Terraform state.

The Frappe secret must contain `admin_password`, `db_name`, and `db_password`.
The configurator also receives the AWS-managed RDS master username/password at
task start. It creates the site and installs ERPNext plus both custom apps only
when the site is absent; retries verify the required apps without creating a
second site. The control-plane secret must contain `shared_secret`; the OpenAI
secret must contain `api_key`. Task startup fails closed when required values
are absent. An approved operator must run `configure` and `migrate` before
services receive traffic.
The `backup` task writes a logical site backup to encrypted EFS, uploads and
verifies its four artifacts in the versioned SSE-KMS bucket, and publishes its
manifest last. EventBridge enables the daily task only after service activation;
a missing success metric within 24 hours alerts the approved external SNS topic.
The protected `production-restore-drill.yml` workflow restores a selected
complete manifest only into a generated disposable internal site, validates
required apps, roles, and transaction links, deletes that site and database,
and retains only aggregate private evidence. Its one-off Fargate execution is
human-authorized separately from deployment; a missing success metric for seven
days alerts operations. A green code check is not deployment restore evidence.

The protected `production-capacity.yml` workflow runs the exact tracked
synthetic service profile in a disposable site. Its task-local AI sidecar uses
the deterministic template provider and has no OpenAI key. The capacity task
publishes aggregate-only KMS-encrypted evidence under `release-evidence/`, emits
the `AIERP/Capacity` success metric, and deletes its generated site and database.
This is a separately authorized billable workload; Terraform validation and a
checked-in task definition are not capacity evidence.
