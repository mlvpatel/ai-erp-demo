#!/usr/bin/env bash
set -euo pipefail

operation="${1:-}"
case "${operation}" in
  configure|migrate|backup) ;;
  *)
    echo "usage: run-ecs-operation.sh {configure|migrate|backup}" >&2
    exit 64
    ;;
esac

terraform_root="${TERRAFORM_ROOT:-infra/aws/terraform}"
cluster="$(terraform -chdir="${terraform_root}" output -raw ecs_cluster_arn)"
task_definition="$(terraform -chdir="${terraform_root}" output -json on_demand_task_definition_arns | jq -r --arg operation "${operation}" '.[$operation]')"
subnets="$(terraform -chdir="${terraform_root}" output -json private_subnet_ids | jq -r 'join(",")')"
security_group="$(terraform -chdir="${terraform_root}" output -raw workload_security_group_id)"

test -n "${cluster}"
test -n "${task_definition}"
test -n "${subnets}"
test -n "${security_group}"

task_arn="$(aws ecs run-task \
  --cluster "${cluster}" \
  --task-definition "${task_definition}" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${subnets}],securityGroups=[${security_group}],assignPublicIp=DISABLED}" \
  --started-by "ai-erp-${operation}-${GITHUB_RUN_ID:-operator}" \
  --query 'tasks[0].taskArn' \
  --output text)"

if [ -z "${task_arn}" ] || [ "${task_arn}" = "None" ]; then
  echo "ECS did not start the ${operation} task" >&2
  exit 1
fi

aws ecs wait tasks-stopped --cluster "${cluster}" --tasks "${task_arn}"
exit_code="$(aws ecs describe-tasks \
  --cluster "${cluster}" \
  --tasks "${task_arn}" \
  --query 'tasks[0].containers[0].exitCode' \
  --output text)"
stop_reason="$(aws ecs describe-tasks \
  --cluster "${cluster}" \
  --tasks "${task_arn}" \
  --query 'tasks[0].stoppedReason' \
  --output text)"

if [ "${exit_code}" != "0" ]; then
  echo "${operation} task failed with exit code ${exit_code}: ${stop_reason}" >&2
  exit 1
fi

echo "${operation} task completed successfully (${task_arn})."
