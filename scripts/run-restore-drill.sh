#!/usr/bin/env bash
set -euo pipefail

manifest_uri="${1:-}"
if [[ ! "${manifest_uri}" =~ ^s3://[a-z0-9.-]+/sites/.+/manifest[.]json$ ]]; then
  echo "usage: run-restore-drill.sh s3://approved-bucket/sites/.../manifest.json" >&2
  exit 64
fi

terraform_root="${TERRAFORM_ROOT:-infra/aws/terraform}"
target_site="restore-drill-${GITHUB_RUN_ID:-operator}.internal"
runner_temp="${RUNNER_TEMP:-/tmp}"
overrides="${runner_temp}/restore-overrides.json"
evidence="${runner_temp}/restore-drill-evidence.json"
trap 'rm -f "${overrides}"' EXIT

cluster="$(terraform -chdir="${terraform_root}" output -raw ecs_cluster_arn)"
task_definition="$(terraform -chdir="${terraform_root}" output -json on_demand_task_definition_arns | jq -r '.restore')"
subnets="$(terraform -chdir="${terraform_root}" output -json private_subnet_ids | jq -r 'join(",")')"
security_group="$(terraform -chdir="${terraform_root}" output -raw workload_security_group_id)"

jq -n \
  --arg target "${target_site}" \
  --arg manifest "${manifest_uri}" \
  '{containerOverrides:[{name:"restore",environment:[{name:"ALLOW_RESTORE_DRILL",value:"I_ACKNOWLEDGE_DISPOSABLE_RESTORE"},{name:"RESTORE_TARGET_SITE",value:$target},{name:"RESTORE_MANIFEST_S3_URI",value:$manifest}]}]}' \
  >"${overrides}"

task_arn="$(aws ecs run-task \
  --cluster "${cluster}" \
  --task-definition "${task_definition}" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${subnets}],securityGroups=[${security_group}],assignPublicIp=DISABLED}" \
  --overrides "file://${overrides}" \
  --started-by "ai-erp-restore-drill-${GITHUB_RUN_ID:-operator}" \
  --query 'tasks[0].taskArn' \
  --output text)"

if [ -z "${task_arn}" ] || [ "${task_arn}" = "None" ]; then
  echo "ECS did not start the disposable restore drill" >&2
  exit 1
fi
aws ecs wait tasks-stopped --cluster "${cluster}" --tasks "${task_arn}"
exit_code="$(aws ecs describe-tasks --cluster "${cluster}" --tasks "${task_arn}" --query 'tasks[0].containers[0].exitCode' --output text)"
if [ "${exit_code}" != "0" ]; then
  echo "disposable restore drill failed; inspect private redacted operations telemetry" >&2
  exit 1
fi

jq -n --arg commit "${GITHUB_SHA:-operator}" --arg run "${GITHUB_RUN_ID:-operator}" \
  '{schema_version:1,status:"PASS",backup_verified:true,restore_validated:true,disposable_site_deleted:true,commit:$commit,workflow_run:$run}' \
  >"${evidence}"
echo "disposable restore, integrity validation, and deletion drill passed."
