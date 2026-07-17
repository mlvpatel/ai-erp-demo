#!/usr/bin/env bash
set -euo pipefail

terraform_root="${TERRAFORM_ROOT:-infra/aws/terraform}"
runner_temp="${RUNNER_TEMP:-/tmp}"
target_site="capacity-run-${GITHUB_RUN_ID:-operator}.internal"
evidence_key="release-evidence/${GITHUB_SHA:-operator}/capacity/${GITHUB_RUN_ID:-operator}.json"
overrides="${runner_temp}/capacity-overrides.json"
evidence="${runner_temp}/capacity-evidence.json"
trap 'rm -f "${overrides}"' EXIT

if [[ ! "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]] || [[ ! "${GITHUB_RUN_ID:-}" =~ ^[0-9]+$ ]]; then
  echo "a protected GitHub commit and workflow run are required" >&2
  exit 64
fi

cluster="$(terraform -chdir="${terraform_root}" output -raw ecs_cluster_arn)"
task_definition="$(terraform -chdir="${terraform_root}" output -raw capacity_task_definition_arn)"
subnets="$(terraform -chdir="${terraform_root}" output -json private_subnet_ids | jq -r 'join(",")')"
security_group="$(terraform -chdir="${terraform_root}" output -raw workload_security_group_id)"
bucket="$(terraform -chdir="${terraform_root}" output -raw backup_bucket_name)"

jq -n \
  --arg target "${target_site}" \
  --arg key "${evidence_key}" \
  --arg commit "${GITHUB_SHA}" \
  --arg run "${GITHUB_RUN_ID}" \
  '{containerOverrides:[{name:"capacity",environment:[{name:"CAPACITY_TARGET_SITE",value:$target},{name:"CAPACITY_EVIDENCE_S3_KEY",value:$key},{name:"CAPACITY_COMMIT",value:$commit},{name:"CAPACITY_WORKFLOW_RUN",value:$run}]}]}' \
  >"${overrides}"

task_arn="$(aws ecs run-task \
  --cluster "${cluster}" \
  --task-definition "${task_definition}" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${subnets}],securityGroups=[${security_group}],assignPublicIp=DISABLED}" \
  --overrides "file://${overrides}" \
  --started-by "ai-erp-capacity-${GITHUB_RUN_ID}" \
  --query 'tasks[0].taskArn' \
  --output text)"

if [ -z "${task_arn}" ] || [ "${task_arn}" = "None" ]; then
  echo "ECS did not start the disposable capacity task" >&2
  exit 1
fi

while [ "$(aws ecs describe-tasks --cluster "${cluster}" --tasks "${task_arn}" --query 'tasks[0].lastStatus' --output text)" != "STOPPED" ]; do
  sleep 30
done

exit_code="$(aws ecs describe-tasks --cluster "${cluster}" --tasks "${task_arn}" --query 'tasks[0].containers[?name==`capacity`].exitCode | [0]' --output text)"
if [ "${exit_code}" != "0" ]; then
  echo "synthetic full capacity task failed; inspect private payload-free operations telemetry" >&2
  exit 1
fi

aws s3 cp "s3://${bucket}/${evidence_key}" "${evidence}" --only-show-errors
python3 scripts/check-capacity-evidence.py "${evidence}"
echo "synthetic full capacity profile and ten-request authenticated concurrency gate passed."
