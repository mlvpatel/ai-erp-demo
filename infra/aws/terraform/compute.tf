resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ai-erp/${var.environment}/ecs"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.platform.arn
}
resource "aws_ecs_cluster" "this" {
  name = local.name

  configuration {
    execute_command_configuration {
      kms_key_id = aws_kms_key.platform.arn
      logging    = "OVERRIDE"
      log_configuration {
        cloud_watch_encryption_enabled = true
        cloud_watch_log_group_name     = aws_cloudwatch_log_group.ecs.name
      }
    }
  }

  setting {
    name  = "containerInsights"
    value = "enhanced"
  }
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = aws_ecs_cluster.this.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    base              = 1
    weight            = 1
  }
}
