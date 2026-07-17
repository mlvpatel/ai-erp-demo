provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "AI ERP Demo"
      Environment = "recovery"
      ManagedBy   = "Terraform"
      RecoveryId  = var.recovery_id
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_vpc" "selected" { id = var.vpc_id }
data "aws_prefix_list" "s3" { name = "com.amazonaws.${var.aws_region}.s3" }

locals {
  name = "ai-erp-recovery-${var.recovery_id}"
}

resource "aws_security_group" "recovery" {
  name        = local.name
  description = "Disposable isolated recovery task"
  vpc_id      = var.vpc_id
}

resource "aws_security_group" "database" {
  name        = "${local.name}-database"
  description = "Disposable recovery database"
  vpc_id      = var.vpc_id
}

resource "aws_security_group" "efs" {
  name        = "${local.name}-efs"
  description = "Disposable recovery EFS"
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "database" {
  security_group_id            = aws_security_group.database.id
  referenced_security_group_id = aws_security_group.recovery.id
  from_port                    = 3306
  to_port                      = 3306
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "efs" {
  security_group_id            = aws_security_group.efs.id
  referenced_security_group_id = aws_security_group.recovery.id
  from_port                    = 2049
  to_port                      = 2049
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "endpoints" {
  security_group_id            = aws_security_group.recovery.id
  referenced_security_group_id = var.endpoint_security_group_id
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "dns_udp" {
  security_group_id = aws_security_group.recovery.id
  cidr_ipv4         = "${cidrhost(data.aws_vpc.selected.cidr_block, 2)}/32"
  from_port         = 53
  to_port           = 53
  ip_protocol       = "udp"
}

resource "aws_vpc_security_group_egress_rule" "dns_tcp" {
  security_group_id = aws_security_group.recovery.id
  cidr_ipv4         = "${cidrhost(data.aws_vpc.selected.cidr_block, 2)}/32"
  from_port         = 53
  to_port           = 53
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "s3" {
  security_group_id = aws_security_group.recovery.id
  prefix_list_id    = data.aws_prefix_list.s3.id
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "production_endpoints" {
  security_group_id            = var.endpoint_security_group_id
  referenced_security_group_id = aws_security_group.recovery.id
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "database" {
  security_group_id            = aws_security_group.recovery.id
  referenced_security_group_id = aws_security_group.database.id
  from_port                    = 3306
  to_port                      = 3306
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "efs" {
  security_group_id            = aws_security_group.recovery.id
  referenced_security_group_id = aws_security_group.efs.id
  from_port                    = 2049
  to_port                      = 2049
  ip_protocol                  = "tcp"
}

resource "aws_db_subnet_group" "recovery" {
  name       = local.name
  subnet_ids = var.private_subnet_ids
}

resource "aws_db_parameter_group" "tls" {
  name   = "${local.name}-tls"
  family = "mariadb11.4"
  parameter {
    name         = "require_secure_transport"
    value        = "ON"
    apply_method = "pending-reboot"
  }
}

resource "aws_db_instance" "recovery" {
  identifier                    = local.name
  engine                        = "mariadb"
  engine_version                = "11.4"
  instance_class                = "db.t4g.micro"
  allocated_storage             = 20
  storage_type                  = "gp3"
  storage_encrypted             = true
  kms_key_id                    = var.platform_kms_key_arn
  username                      = "recoveryadmin"
  manage_master_user_password   = true
  master_user_secret_kms_key_id = var.platform_kms_key_arn
  multi_az                      = false
  publicly_accessible           = false
  db_subnet_group_name          = aws_db_subnet_group.recovery.name
  parameter_group_name          = aws_db_parameter_group.tls.name
  vpc_security_group_ids        = [aws_security_group.database.id]
  backup_retention_period       = 0
  deletion_protection           = false
  skip_final_snapshot           = true
}

resource "aws_efs_file_system" "recovery" {
  encrypted        = true
  kms_key_id       = var.platform_kms_key_arn
  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"
}

resource "aws_efs_mount_target" "recovery" {
  for_each        = toset(var.private_subnet_ids)
  file_system_id  = aws_efs_file_system.recovery.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "recovery" {
  file_system_id = aws_efs_file_system.recovery.id
  posix_user {
    gid = 1000
    uid = 1000
  }
  root_directory {
    path = "/sites"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "0750"
    }
  }
}

resource "aws_cloudwatch_log_group" "recovery" {
  name              = "/ai-erp/recovery/${var.recovery_id}"
  retention_in_days = 14
  kms_key_id        = var.platform_kms_key_arn
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${local.name}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "recovery_secret" {
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      var.frappe_secret_arn,
      aws_db_instance.recovery.master_user_secret[0].secret_arn,
    ]
  }
  statement {
    actions   = ["kms:Decrypt"]
    resources = [var.platform_kms_key_arn]
  }
}

resource "aws_iam_role_policy" "recovery_secret" {
  name   = "recovery-${var.recovery_id}"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.recovery_secret.json
}

resource "aws_ecs_task_definition" "recovery" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = var.ecs_operation_role_arn
  volume {
    name = "sites"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.recovery.id
      transit_encryption = "ENABLED"
      authorization_config { access_point_id = aws_efs_access_point.recovery.id }
    }
  }
  volume { name = "tmp" }
  container_definitions = jsonencode([{
    name      = "restore"
    image     = var.frappe_backend_image
    essential = true
    command   = ["/opt/ai-erp/bin/runtime", "restore"]
    environment = [
      { name = "DB_HOST", value = aws_db_instance.recovery.address },
      { name = "DB_SSL_CA", value = "/etc/ssl/certs/ca-certificates.crt" },
      { name = "BACKUP_BUCKET", value = var.backup_bucket_name },
      { name = "BACKUP_KMS_KEY_ARN", value = var.platform_kms_key_arn },
      { name = "DEPLOYMENT_ENVIRONMENT", value = "pilot" },
    ]
    secrets = [
      { name = "DB_ROOT_USERNAME", valueFrom = "${aws_db_instance.recovery.master_user_secret[0].secret_arn}:username::" },
      { name = "DB_ROOT_PASSWORD", valueFrom = "${aws_db_instance.recovery.master_user_secret[0].secret_arn}:password::" },
      { name = "FRAPPE_ADMIN_PASSWORD", valueFrom = "${var.frappe_secret_arn}:admin_password::" },
    ]
    mountPoints = [
      { sourceVolume = "sites", containerPath = "/home/frappe/frappe-bench/sites", readOnly = false },
      { sourceVolume = "tmp", containerPath = "/tmp", readOnly = false },
    ]
    readonlyRootFilesystem = true
    linuxParameters        = { initProcessEnabled = true }
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.recovery.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "recovery"
      }
    }
  }])
  depends_on = [aws_efs_mount_target.recovery]
}

check "approved_account" {
  assert {
    condition     = data.aws_caller_identity.current.account_id == var.aws_account_id
    error_message = "Recovery stack account mismatch."
  }
}
