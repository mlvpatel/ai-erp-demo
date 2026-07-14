resource "aws_db_subnet_group" "this" {
  name       = local.name
  subnet_ids = values(aws_subnet.private)[*].id
}

resource "aws_db_instance" "mariadb" {
  identifier                    = "${local.name}-mariadb"
  engine                        = "mariadb"
  instance_class                = var.db_instance_class
  allocated_storage             = 40
  max_allocated_storage         = 200
  storage_type                  = "gp3"
  storage_encrypted             = true
  kms_key_id                    = aws_kms_key.platform.arn
  username                      = "erpadmin"
  manage_master_user_password   = true
  master_user_secret_kms_key_id = aws_kms_key.platform.arn
  multi_az                      = true
  publicly_accessible           = false
  db_subnet_group_name          = aws_db_subnet_group.this.name
  vpc_security_group_ids        = [aws_security_group.database.id]
  backup_retention_period       = var.backup_retention_days
  copy_tags_to_snapshot         = true
  deletion_protection           = true
  skip_final_snapshot           = false
  final_snapshot_identifier     = "${local.name}-final"
  auto_minor_version_upgrade    = true
  apply_immediately             = false

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_elasticache_subnet_group" "this" {
  name       = local.name
  subnet_ids = values(aws_subnet.private)[*].id
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${local.name}-redis"
  description                = "AI ERP encrypted queue and cache"
  engine                     = "valkey"
  node_type                  = var.redis_node_type
  port                       = 6379
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  multi_az_enabled           = true
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                 = aws_kms_key.platform.arn
  subnet_group_name          = aws_elasticache_subnet_group.this.name
  security_group_ids         = [aws_security_group.redis.id]
  snapshot_retention_limit   = var.backup_retention_days
  apply_immediately          = false

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_efs_file_system" "sites" {
  encrypted        = true
  kms_key_id       = aws_kms_key.platform.arn
  performance_mode = "generalPurpose"
  throughput_mode  = "elastic"
  tags             = { Name = "${local.name}-sites" }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_efs_backup_policy" "sites" {
  file_system_id = aws_efs_file_system.sites.id
  backup_policy {
    status = "ENABLED"
  }
}

resource "aws_efs_mount_target" "sites" {
  for_each        = aws_subnet.private
  file_system_id  = aws_efs_file_system.sites.id
  subnet_id       = each.value.id
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "sites" {
  file_system_id = aws_efs_file_system.sites.id
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

resource "aws_s3_bucket" "backups" {
  bucket_prefix = "${local.name}-backups-"
  force_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket                  = aws_s3_bucket.backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    bucket_key_enabled = true
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.platform.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    id     = "retention"
    status = "Enabled"
    filter {}
    expiration {
      days = var.logical_backup_retention_days
    }
    noncurrent_version_expiration {
      noncurrent_days = var.logical_backup_retention_days
    }
  }
}

data "aws_iam_policy_document" "backup_bucket" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.backups.arn,
      "${aws_s3_bucket.backups.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "backups" {
  bucket = aws_s3_bucket.backups.id
  policy = data.aws_iam_policy_document.backup_bucket.json
}
