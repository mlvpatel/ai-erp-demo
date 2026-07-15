# One-time AWS production bootstrap

This separate root creates only the prerequisites that must exist before the
main pilot stack can build images or use remote state: an encrypted,
access-logged and versioned state bucket, a GitHub OIDC provider restricted to
the protected `production` environment, immutable ECR repositories, a private
KMS image-signing key, and a least-privilege image-publisher role.
It also creates a separate protected Terraform deploy role. That role uses
`PowerUserAccess` for regional service resources plus narrowly named IAM and
remote-state permissions; it cannot be assumed outside the repository's
protected `production` environment.

Run it only from an approved administrator session after the ADR-0007 account,
budget, repository, and support gates are accepted. Keep its local bootstrap
state in an approved encrypted operations store; never commit state, plans,
account IDs, or backend files. After applying, configure the protected GitHub
environment variables from the non-secret outputs:

- `AWS_ACCOUNT_ID`
- `AWS_IMAGE_PUBLISH_ROLE_ARN`
- `AWS_TERRAFORM_DEPLOY_ROLE_ARN`
- `AWS_TERRAFORM_STATE_BUCKET`
- `AWS_TERRAFORM_STATE_KMS_KEY_ARN`
- `ALERT_TOPIC_ARN`
- `COSIGN_KMS_KEY_URI`
- the three reviewed base-image digest variables

The GitHub OIDC trust is bound to
`repo:mlvpatel/ai-erp-demo:environment:production` by default. Changing the
repository or environment requires a reviewed plan.

The bootstrap creates an encrypted SNS topic whose resource policy accepts
publishes only from this account's CloudWatch and AWS Budgets services. Add and
confirm subscriber endpoints manually in the AWS console so operator email,
phone, or incident-routing identities never enter Terraform state or Git.

Credential-free checks use Terraform 1.13.5:

```sh
terraform -chdir=infra/aws/bootstrap fmt -check -recursive
terraform -chdir=infra/aws/bootstrap init -backend=false
terraform -chdir=infra/aws/bootstrap validate
```

This bootstrap does not authorize the balanced-pilot stack, publish an image,
seed a secret, or run `terraform apply` from CI.
