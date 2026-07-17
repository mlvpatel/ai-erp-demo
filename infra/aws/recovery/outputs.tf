output "ecs_cluster_arn" { value = var.ecs_cluster_arn }
output "private_subnet_ids" { value = var.private_subnet_ids }
output "workload_security_group_id" { value = aws_security_group.recovery.id }
output "on_demand_task_definition_arns" {
  value = { restore = aws_ecs_task_definition.recovery.arn }
}
