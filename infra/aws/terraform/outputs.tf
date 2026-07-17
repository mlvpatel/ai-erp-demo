output "vpc_id" {
  value = aws_vpc.this.id
}

output "private_subnet_ids" {
  value = values(aws_subnet.private)[*].id
}

output "ecs_cluster_arn" {
  value = aws_ecs_cluster.this.arn
}

output "ecs_service_names" {
  value = merge(
    { web = aws_ecs_service.web.name, ai = aws_ecs_service.ai.name },
    { for key, service in aws_ecs_service.frappe : key => service.name },
  )
}

output "on_demand_task_definition_arns" {
  description = "Reviewed task definitions; Terraform does not run them."
  value       = { for key, task in aws_ecs_task_definition.operation : key => task.arn }
}

output "ai_live_eval_task_definition_arn" {
  description = "Private bounded synthetic OpenAI evaluation task."
  value       = aws_ecs_task_definition.ai_live_eval.arn
}

output "capacity_task_definition_arn" {
  description = "Disposable exact-volume synthetic capacity task."
  value       = aws_ecs_task_definition.capacity.arn
}

output "workload_security_group_id" {
  value = aws_security_group.workload.id
}

output "ai_security_group_id" {
  value = aws_security_group.ai.id
}

output "endpoint_security_group_id" {
  value = aws_security_group.endpoints.id
}

output "alb_dns_name" {
  value = aws_lb.this.dns_name
}

output "web_target_group_arn" {
  value = aws_lb_target_group.web.arn
}

output "websocket_target_group_arn" {
  value = aws_lb_target_group.websocket.arn
}

output "database_endpoint" {
  value = aws_db_instance.mariadb.address
}

output "database_master_secret_arn" {
  value = aws_db_instance.mariadb.master_user_secret[0].secret_arn
}

output "redis_primary_endpoint" {
  value = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "efs_file_system_id" {
  value = aws_efs_file_system.sites.id
}

output "efs_access_point_id" {
  value = aws_efs_access_point.sites.id
}

output "backup_bucket_name" {
  value = aws_s3_bucket.backups.id
}

output "frappe_secret_arn" {
  value = aws_secretsmanager_secret.frappe.arn
}

output "control_plane_secret_arn" {
  value = aws_secretsmanager_secret.control_plane.arn
}

output "openai_secret_arn" {
  value = aws_secretsmanager_secret.openai.arn
}

output "ecs_execution_role_name" {
  value = aws_iam_role.ecs_execution.name
}

output "ecs_operation_role_arn" {
  value = aws_iam_role.ecs_operation.arn
}

output "platform_kms_key_arn" {
  value = aws_kms_key.platform.arn
}

output "frappe_backend_image" {
  value = var.frappe_backend_image
}
