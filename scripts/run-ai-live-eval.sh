#!/usr/bin/env bash
set -euo pipefail

terraform_root="${TERRAFORM_ROOT:-infra/aws/terraform}"
cluster="$(terraform -chdir="${terraform_root}" output -raw ecs_cluster_arn)"
task_definition="$(terraform -chdir="${terraform_root}" output -raw ai_live_eval_task_definition_arn)"
subnets="$(terraform -chdir="${terraform_root}" output -json private_subnet_ids | jq -r 'join(",")')"
security_group="$(terraform -chdir="${terraform_root}" output -raw workload_security_group_id)"

task_arn="$(aws ecs run-task \
  --cluster "${cluster}" \
  --task-definition "${task_definition}" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${subnets}],securityGroups=[${security_group}],assignPublicIp=DISABLED}" \
  --started-by "ai-erp-live-eval-${GITHUB_RUN_ID:-operator}" \
  --query 'tasks[0].taskArn' \
  --output text)"

if [ -z "${task_arn}" ] || [ "${task_arn}" = "None" ]; then
  echo "ECS did not start the private live evaluation task" >&2
  exit 1
fi

aws ecs wait tasks-stopped --cluster "${cluster}" --tasks "${task_arn}"
exit_code="$(aws ecs describe-tasks --cluster "${cluster}" --tasks "${task_arn}" --query 'tasks[0].containers[0].exitCode' --output text)"
if [ "${exit_code}" != "0" ]; then
  echo "private synthetic OpenAI evaluation failed; inspect redacted operations telemetry" >&2
  exit 1
fi
echo "private synthetic OpenAI evaluation passed (one bounded case)."
