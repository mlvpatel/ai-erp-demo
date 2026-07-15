resource "aws_cloudwatch_log_group" "ecs" {
  for_each          = toset(["web", "websocket", "scheduler", "worker-short", "worker-long", "ai", "operations"])
  name              = "/ai-erp/${var.environment}/${each.key}"
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
        cloud_watch_log_group_name     = aws_cloudwatch_log_group.ecs["operations"].name
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

resource "aws_service_discovery_private_dns_namespace" "this" {
  name        = "${var.environment}.ai-erp.internal"
  description = "Private service discovery for the AI ERP pilot"
  vpc         = aws_vpc.this.id
}

resource "aws_service_discovery_service" "ai" {
  name = "ai-control-plane"
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.this.id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }
  health_check_custom_config {}
}

resource "aws_service_discovery_service" "websocket" {
  name = "websocket"
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.this.id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }
  health_check_custom_config {}
}

locals {
  frappe_environment = [
    { name = "SITE_NAME", value = var.domain_name },
    { name = "DB_HOST", value = aws_db_instance.mariadb.address },
    { name = "REDIS_CACHE", value = "rediss://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379" },
    { name = "REDIS_QUEUE", value = "rediss://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379" },
    { name = "AI_CONTROL_PLANE_URL", value = "http://ai-control-plane.${aws_service_discovery_private_dns_namespace.this.name}:8090" },
  ]
  log_options = {
    "awslogs-region"        = var.aws_region
    "awslogs-stream-prefix" = "ecs"
  }
  service_profiles = {
    websocket = {
      command = ["/opt/ai-erp/bin/runtime", "websocket"]
      cpu     = 256
      memory  = 512
      desired = 1
      minimum = 1
      maximum = 1
      port    = 9000
    }
    scheduler = {
      command = ["/opt/ai-erp/bin/runtime", "scheduler"]
      cpu     = 256
      memory  = 512
      desired = 1
      minimum = 1
      maximum = 1
      port    = 0
    }
    worker-short = {
      command = ["/opt/ai-erp/bin/runtime", "worker-short"]
      cpu     = 512
      memory  = 1024
      desired = 1
      minimum = 1
      maximum = 2
      port    = 0
    }
    worker-long = {
      command = ["/opt/ai-erp/bin/runtime", "worker-long"]
      cpu     = 512
      memory  = 1024
      desired = 1
      minimum = 1
      maximum = 1
      port    = 0
    }
  }
}

resource "aws_ecs_task_definition" "web" {
  family                   = "${local.name}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  volume {
    name = "sites"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.sites.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.sites.id
      }
    }
  }
  volume { name = "logs" }
  volume { name = "tmp" }
  volume { name = "nginx-cache" }
  volume { name = "nginx-run" }

  container_definitions = jsonencode([
    {
      name        = "backend"
      image       = var.frappe_backend_image
      essential   = true
      command     = ["/opt/ai-erp/bin/runtime", "web"]
      environment = local.frappe_environment
      secrets = [{
        name      = "AI_CONTROL_PLANE_SHARED_SECRET"
        valueFrom = "${aws_secretsmanager_secret.control_plane.arn}:shared_secret::"
      }]
      portMappings = [{ containerPort = 8000, hostPort = 8000, protocol = "tcp" }]
      mountPoints = [
        { sourceVolume = "sites", containerPath = "/home/frappe/frappe-bench/sites", readOnly = false },
        { sourceVolume = "logs", containerPath = "/home/frappe/frappe-bench/logs", readOnly = false },
        { sourceVolume = "tmp", containerPath = "/tmp", readOnly = false },
      ]
      readonlyRootFilesystem = true
      linuxParameters        = { initProcessEnabled = true }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import os; from urllib.request import Request,urlopen; urlopen(Request('http://127.0.0.1:8000/api/method/ping',headers={'Host':os.environ['SITE_NAME']}))\""]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
      logConfiguration = {
        logDriver = "awslogs"
        options   = merge(local.log_options, { "awslogs-group" = aws_cloudwatch_log_group.ecs["web"].name })
      }
    },
    {
      name      = "frontend"
      image     = var.frappe_frontend_image
      essential = true
      environment = [
        { name = "BACKEND", value = "127.0.0.1:8000" },
        { name = "SOCKETIO", value = "websocket.${aws_service_discovery_private_dns_namespace.this.name}:9000" },
        { name = "FRAPPE_SITE_NAME_HEADER", value = var.domain_name },
      ]
      dependsOn    = [{ containerName = "backend", condition = "HEALTHY" }]
      portMappings = [{ containerPort = 8080, hostPort = 8080, protocol = "tcp" }]
      mountPoints = [
        { sourceVolume = "nginx-cache", containerPath = "/var/cache/nginx", readOnly = false },
        { sourceVolume = "nginx-run", containerPath = "/var/run", readOnly = false },
        { sourceVolume = "tmp", containerPath = "/tmp", readOnly = false },
      ]
      readonlyRootFilesystem = true
      linuxParameters        = { initProcessEnabled = true }
      logConfiguration = {
        logDriver = "awslogs"
        options   = merge(local.log_options, { "awslogs-group" = aws_cloudwatch_log_group.ecs["web"].name })
      }
    },
  ])
}

resource "aws_ecs_task_definition" "frappe_service" {
  for_each                 = local.service_profiles
  family                   = "${local.name}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  volume {
    name = "sites"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.sites.id
      transit_encryption = "ENABLED"
      authorization_config { access_point_id = aws_efs_access_point.sites.id }
    }
  }
  volume { name = "logs" }
  volume { name = "tmp" }

  container_definitions = jsonencode([{
    name         = each.key
    image        = var.frappe_backend_image
    essential    = true
    command      = each.value.command
    environment  = local.frappe_environment
    portMappings = each.value.port == 0 ? [] : [{ containerPort = each.value.port, hostPort = each.value.port, protocol = "tcp" }]
    mountPoints = [
      { sourceVolume = "sites", containerPath = "/home/frappe/frappe-bench/sites", readOnly = false },
      { sourceVolume = "logs", containerPath = "/home/frappe/frappe-bench/logs", readOnly = false },
      { sourceVolume = "tmp", containerPath = "/tmp", readOnly = false },
    ]
    readonlyRootFilesystem = true
    linuxParameters        = { initProcessEnabled = true }
    logConfiguration = {
      logDriver = "awslogs"
      options   = merge(local.log_options, { "awslogs-group" = aws_cloudwatch_log_group.ecs[each.key].name })
    }
  }])
}

resource "aws_ecs_task_definition" "ai" {
  family                   = "${local.name}-ai"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn
  volume { name = "tmp" }
  container_definitions = jsonencode([{
    name         = "ai"
    image        = var.ai_control_plane_image
    essential    = true
    portMappings = [{ containerPort = 8090, hostPort = 8090, protocol = "tcp" }]
    environment = [
      { name = "AI_ERP_PROVIDER", value = "openai" },
      { name = "OPENAI_BASE_URL", value = "https://eu.api.openai.com/v1" },
      { name = "OPENAI_MODEL", value = "gpt-5.4-mini-2026-03-17" },
      { name = "OPENAI_TIMEOUT_SECONDS", value = "20" },
    ]
    secrets = [
      { name = "AI_CONTROL_PLANE_SHARED_SECRET", valueFrom = "${aws_secretsmanager_secret.control_plane.arn}:shared_secret::" },
      { name = "OPENAI_API_KEY", valueFrom = "${aws_secretsmanager_secret.openai.arn}:api_key::" },
    ]
    readonlyRootFilesystem = true
    mountPoints            = [{ sourceVolume = "tmp", containerPath = "/tmp", readOnly = false }]
    linuxParameters        = { initProcessEnabled = true }
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"from urllib.request import urlopen; urlopen('http://127.0.0.1:8090/healthz')\""]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 20
    }
    logConfiguration = {
      logDriver = "awslogs"
      options   = merge(local.log_options, { "awslogs-group" = aws_cloudwatch_log_group.ecs["ai"].name })
    }
  }])
}

resource "aws_ecs_task_definition" "ai_live_eval" {
  family                   = "${local.name}-ai-live-eval"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn
  volume { name = "tmp" }
  container_definitions = jsonencode([{
    name      = "ai-live-eval"
    image     = var.ai_control_plane_image
    essential = true
    command   = ["python", "-m", "ai_erp_control_plane.live_eval"]
    environment = [
      { name = "AI_ERP_PROVIDER", value = "openai" },
      { name = "OPENAI_BASE_URL", value = "https://eu.api.openai.com/v1" },
      { name = "OPENAI_MODEL", value = "gpt-5.4-mini-2026-03-17" },
      { name = "OPENAI_TIMEOUT_SECONDS", value = "20" },
      { name = "OPENAI_API_KEY_SOURCE", value = "deployment-secret-store" },
      { name = "AI_ERP_ENABLE_PRIVATE_LIVE_EVAL", value = "I_ACKNOWLEDGE_SYNTHETIC_ONLY" },
    ]
    secrets = [
      { name = "OPENAI_API_KEY", valueFrom = "${aws_secretsmanager_secret.openai.arn}:api_key::" },
    ]
    readonlyRootFilesystem = true
    mountPoints            = [{ sourceVolume = "tmp", containerPath = "/tmp", readOnly = false }]
    linuxParameters        = { initProcessEnabled = true }
    logConfiguration = {
      logDriver = "awslogs"
      options   = merge(local.log_options, { "awslogs-group" = aws_cloudwatch_log_group.ecs["operations"].name })
    }
  }])
}

resource "aws_ecs_task_definition" "capacity" {
  family                   = "${local.name}-capacity"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 2048
  memory                   = 4096
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_operation.arn
  volume {
    name = "sites"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.sites.id
      transit_encryption = "ENABLED"
      authorization_config { access_point_id = aws_efs_access_point.sites.id }
    }
  }
  volume { name = "logs" }
  volume { name = "tmp" }
  container_definitions = jsonencode([
    {
      name      = "capacity"
      image     = var.frappe_backend_image
      essential = true
      command   = ["/opt/ai-erp/bin/runtime", "capacity"]
      cpu       = 1792
      memory    = 3584
      environment = concat(
        [for setting in local.frappe_environment : setting if setting.name != "AI_CONTROL_PLANE_URL"],
        [
          { name = "AI_CONTROL_PLANE_URL", value = "http://127.0.0.1:8090" },
          { name = "AI_ERP_PROVIDER", value = "template" },
          { name = "AI_ERP_FULL_CAPACITY_ALLOW", value = "I_ACKNOWLEDGE_DISPOSABLE_SYNTHETIC_CAPACITY" },
          { name = "CAPACITY_EVIDENCE_PATH", value = "/tmp/ai-erp-capacity-evidence.json" },
          { name = "CAPACITY_SAMPLES", value = "100" },
          { name = "BACKUP_BUCKET", value = aws_s3_bucket.backups.id },
          { name = "BACKUP_KMS_KEY_ARN", value = aws_kms_key.platform.arn },
          { name = "DEPLOYMENT_ENVIRONMENT", value = var.environment },
        ],
      )
      secrets = [
        { name = "DB_ROOT_USERNAME", valueFrom = "${aws_db_instance.mariadb.master_user_secret[0].secret_arn}:username::" },
        { name = "DB_ROOT_PASSWORD", valueFrom = "${aws_db_instance.mariadb.master_user_secret[0].secret_arn}:password::" },
        { name = "FRAPPE_ADMIN_PASSWORD", valueFrom = "${aws_secretsmanager_secret.frappe.arn}:admin_password::" },
        { name = "AI_CONTROL_PLANE_SHARED_SECRET", valueFrom = "${aws_secretsmanager_secret.control_plane.arn}:shared_secret::" },
      ]
      dependsOn = [{ containerName = "capacity-ai-template", condition = "HEALTHY" }]
      mountPoints = [
        { sourceVolume = "sites", containerPath = "/home/frappe/frappe-bench/sites", readOnly = false },
        { sourceVolume = "logs", containerPath = "/home/frappe/frappe-bench/logs", readOnly = false },
        { sourceVolume = "tmp", containerPath = "/tmp", readOnly = false },
      ]
      readonlyRootFilesystem = true
      linuxParameters        = { initProcessEnabled = true }
      logConfiguration = {
        logDriver = "awslogs"
        options   = merge(local.log_options, { "awslogs-group" = aws_cloudwatch_log_group.ecs["operations"].name })
      }
    },
    {
      name      = "capacity-ai-template"
      image     = var.ai_control_plane_image
      essential = true
      cpu       = 256
      memory    = 512
      environment = [
        { name = "AI_ERP_PROVIDER", value = "template" },
      ]
      secrets = [
        { name = "AI_CONTROL_PLANE_SHARED_SECRET", valueFrom = "${aws_secretsmanager_secret.control_plane.arn}:shared_secret::" },
      ]
      readonlyRootFilesystem = true
      mountPoints            = [{ sourceVolume = "tmp", containerPath = "/tmp", readOnly = false }]
      linuxParameters        = { initProcessEnabled = true }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"from urllib.request import urlopen; urlopen('http://127.0.0.1:8090/healthz')\""]
        interval    = 10
        timeout     = 5
        retries     = 6
        startPeriod = 20
      }
      logConfiguration = {
        logDriver = "awslogs"
        options   = merge(local.log_options, { "awslogs-group" = aws_cloudwatch_log_group.ecs["operations"].name })
      }
    },
  ])
}

resource "aws_ecs_task_definition" "operation" {
  for_each                 = toset(["configure", "migrate", "backup", "restore"])
  family                   = "${local.name}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_operation.arn
  volume {
    name = "sites"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.sites.id
      transit_encryption = "ENABLED"
      authorization_config { access_point_id = aws_efs_access_point.sites.id }
    }
  }
  volume { name = "logs" }
  volume { name = "tmp" }
  container_definitions = jsonencode([{
    name      = each.key
    image     = var.frappe_backend_image
    essential = true
    command   = ["/opt/ai-erp/bin/runtime", each.key]
    environment = concat(local.frappe_environment, [
      { name = "BACKUP_BUCKET", value = aws_s3_bucket.backups.id },
      { name = "BACKUP_KMS_KEY_ARN", value = aws_kms_key.platform.arn },
      { name = "DEPLOYMENT_ENVIRONMENT", value = var.environment },
    ])
    secrets = [for secret in [
      { name = "DB_ROOT_USERNAME", valueFrom = "${aws_db_instance.mariadb.master_user_secret[0].secret_arn}:username::", operations = ["configure", "restore"] },
      { name = "DB_ROOT_PASSWORD", valueFrom = "${aws_db_instance.mariadb.master_user_secret[0].secret_arn}:password::", operations = ["configure", "restore"] },
      { name = "FRAPPE_ADMIN_PASSWORD", valueFrom = "${aws_secretsmanager_secret.frappe.arn}:admin_password::", operations = ["configure", "restore"] },
      { name = "FRAPPE_DB_NAME", valueFrom = "${aws_secretsmanager_secret.frappe.arn}:db_name::", operations = ["configure"] },
      { name = "FRAPPE_DB_PASSWORD", valueFrom = "${aws_secretsmanager_secret.frappe.arn}:db_password::", operations = ["configure"] },
      ] : {
      name      = secret.name
      valueFrom = secret.valueFrom
    } if contains(secret.operations, each.key)]
    mountPoints = [
      { sourceVolume = "sites", containerPath = "/home/frappe/frappe-bench/sites", readOnly = false },
      { sourceVolume = "logs", containerPath = "/home/frappe/frappe-bench/logs", readOnly = false },
      { sourceVolume = "tmp", containerPath = "/tmp", readOnly = false },
    ]
    readonlyRootFilesystem = true
    linuxParameters        = { initProcessEnabled = true }
    logConfiguration = {
      logDriver = "awslogs"
      options   = merge(local.log_options, { "awslogs-group" = aws_cloudwatch_log_group.ecs["operations"].name })
    }
  }])
}

data "aws_iam_policy_document" "backup_scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "backup_scheduler" {
  name               = "${local.name}-backup-scheduler"
  assume_role_policy = data.aws_iam_policy_document.backup_scheduler_assume.json
}

data "aws_iam_policy_document" "backup_scheduler" {
  statement {
    actions   = ["ecs:RunTask"]
    resources = [aws_ecs_task_definition.operation["backup"].arn]
  }
  statement {
    actions = ["iam:PassRole"]
    resources = [
      aws_iam_role.ecs_execution.arn,
      aws_iam_role.ecs_operation.arn,
    ]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "backup_scheduler" {
  name   = "run-site-backup-task"
  role   = aws_iam_role.backup_scheduler.id
  policy = data.aws_iam_policy_document.backup_scheduler.json
}

resource "aws_cloudwatch_event_rule" "daily_backup" {
  name                = "${local.name}-daily-backup"
  description         = "Daily encrypted logical Frappe backup"
  schedule_expression = "cron(15 1 * * ? *)"
  state               = var.activate_services ? "ENABLED" : "DISABLED"
}

resource "aws_cloudwatch_event_target" "daily_backup" {
  rule     = aws_cloudwatch_event_rule.daily_backup.name
  arn      = aws_ecs_cluster.this.arn
  role_arn = aws_iam_role.backup_scheduler.arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.operation["backup"].arn
    task_count          = 1
    launch_type         = "FARGATE"
    platform_version    = "LATEST"
    network_configuration {
      subnets          = values(aws_subnet.private)[*].id
      security_groups  = [aws_security_group.workload.id]
      assign_public_ip = false
    }
  }
}

resource "aws_ecs_service" "web" {
  name                               = "${local.name}-web"
  cluster                            = aws_ecs_cluster.this.id
  task_definition                    = aws_ecs_task_definition.web.arn
  desired_count                      = var.activate_services ? 1 : 0
  launch_type                        = "FARGATE"
  platform_version                   = "LATEST"
  health_check_grace_period_seconds  = 120
  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200
  enable_execute_command             = false
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = values(aws_subnet.private)[*].id
    security_groups  = [aws_security_group.workload.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "frontend"
    container_port   = 8080
  }
  depends_on = [aws_lb_listener.https]
}

resource "aws_ecs_service" "frappe" {
  for_each                           = local.service_profiles
  name                               = "${local.name}-${each.key}"
  cluster                            = aws_ecs_cluster.this.id
  task_definition                    = aws_ecs_task_definition.frappe_service[each.key].arn
  desired_count                      = var.activate_services ? each.value.desired : 0
  launch_type                        = "FARGATE"
  platform_version                   = "LATEST"
  health_check_grace_period_seconds  = each.key == "websocket" ? 60 : null
  deployment_minimum_healthy_percent = each.key == "scheduler" ? 0 : 50
  deployment_maximum_percent         = 200
  enable_execute_command             = false
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = values(aws_subnet.private)[*].id
    security_groups  = [aws_security_group.workload.id]
    assign_public_ip = false
  }
  dynamic "load_balancer" {
    for_each = each.key == "websocket" ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.websocket.arn
      container_name   = "websocket"
      container_port   = 9000
    }
  }
  dynamic "service_registries" {
    for_each = each.key == "websocket" ? [1] : []
    content {
      registry_arn = aws_service_discovery_service.websocket.arn
    }
  }
  depends_on = [aws_lb_listener.https]
}

resource "aws_ecs_service" "ai" {
  name                               = "${local.name}-ai"
  cluster                            = aws_ecs_cluster.this.id
  task_definition                    = aws_ecs_task_definition.ai.arn
  desired_count                      = var.activate_services ? 1 : 0
  launch_type                        = "FARGATE"
  platform_version                   = "LATEST"
  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200
  enable_execute_command             = false
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = values(aws_subnet.private)[*].id
    security_groups  = [aws_security_group.workload.id]
    assign_public_ip = false
  }
  service_registries {
    registry_arn = aws_service_discovery_service.ai.arn
  }
}

locals {
  scalable_services = merge(
    { web = { name = aws_ecs_service.web.name, minimum = var.activate_services ? 1 : 0, maximum = 2 } },
    { for key, value in aws_ecs_service.frappe : key => { name = value.name, minimum = var.activate_services ? local.service_profiles[key].minimum : 0, maximum = local.service_profiles[key].maximum } if local.service_profiles[key].maximum > local.service_profiles[key].minimum },
    { ai = { name = aws_ecs_service.ai.name, minimum = var.activate_services ? 1 : 0, maximum = 2 } },
  )
}

resource "aws_appautoscaling_target" "ecs" {
  for_each           = local.scalable_services
  max_capacity       = each.value.maximum
  min_capacity       = each.value.minimum
  resource_id        = "service/${aws_ecs_cluster.this.name}/${each.value.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_cpu" {
  for_each           = local.scalable_services
  name               = "${local.name}-${each.key}-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs[each.key].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs[each.key].scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs[each.key].service_namespace
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 65
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
