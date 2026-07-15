resource "aws_cloudwatch_log_group" "waf" {
  name              = "aws-waf-logs-${local.name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.platform.arn
}

resource "aws_wafv2_web_acl_logging_configuration" "this" {
  log_destination_configs = [aws_cloudwatch_log_group.waf.arn]
  resource_arn            = aws_wafv2_web_acl.this.arn
  redacted_fields {
    single_header {
      name = "authorization"
    }
  }
  redacted_fields {
    single_header {
      name = "cookie"
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "${local.name}-alb-5xx"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_ELB_5XX_Count"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  dimensions          = { LoadBalancer = aws_lb.this.arn_suffix }
  alarm_actions       = [var.alert_topic_arn]
  ok_actions          = [var.alert_topic_arn]
}

resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_targets" {
  for_each            = { web = aws_lb_target_group.web.arn_suffix, websocket = aws_lb_target_group.websocket.arn_suffix }
  alarm_name          = "${local.name}-${each.key}-unhealthy-targets"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "breaching"
  dimensions = {
    LoadBalancer = aws_lb.this.arn_suffix
    TargetGroup  = each.value
  }
  alarm_actions = [var.alert_topic_arn]
  ok_actions    = [var.alert_topic_arn]
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${local.name}-rds-cpu"
  namespace           = "AWS/RDS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 3
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "breaching"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.mariadb.id }
  alarm_actions       = [var.alert_topic_arn]
  ok_actions          = [var.alert_topic_arn]
}

resource "aws_cloudwatch_metric_alarm" "rds_free_storage" {
  alarm_name          = "${local.name}-rds-free-storage"
  namespace           = "AWS/RDS"
  metric_name         = "FreeStorageSpace"
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 10737418240
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.mariadb.id }
  alarm_actions       = [var.alert_topic_arn]
  ok_actions          = [var.alert_topic_arn]
}

resource "aws_cloudwatch_metric_alarm" "redis_evictions" {
  alarm_name          = "${local.name}-redis-evictions"
  namespace           = "AWS/ElastiCache"
  metric_name         = "Evictions"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  dimensions          = { ReplicationGroupId = aws_elasticache_replication_group.redis.id }
  alarm_actions       = [var.alert_topic_arn]
  ok_actions          = [var.alert_topic_arn]
}

resource "aws_budgets_budget" "monthly" {
  name         = "${local.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  dynamic "notification" {
    for_each = toset([50, 80, 100])
    content {
      comparison_operator       = "GREATER_THAN"
      threshold                 = notification.value
      threshold_type            = "PERCENTAGE"
      notification_type         = "ACTUAL"
      subscriber_sns_topic_arns = [var.alert_topic_arn]
    }
  }
}

locals {
  expected_service_counts = merge(
    { web = 1, ai = 1 },
    { for key, value in local.service_profiles : key => value.desired },
  )
}

resource "aws_cloudwatch_metric_alarm" "ecs_running_tasks" {
  for_each            = local.expected_service_counts
  alarm_name          = "${local.name}-${each.key}-running-tasks"
  namespace           = "ECS/ContainerInsights"
  metric_name         = "RunningTaskCount"
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 2
  threshold           = each.value
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  dimensions = {
    ClusterName = aws_ecs_cluster.this.name
    ServiceName = each.key == "web" ? aws_ecs_service.web.name : each.key == "ai" ? aws_ecs_service.ai.name : aws_ecs_service.frappe[each.key].name
  }
  alarm_actions = [var.alert_topic_arn]
  ok_actions    = [var.alert_topic_arn]
}

resource "aws_cloudwatch_metric_alarm" "backup_freshness" {
  alarm_name          = "${local.name}-backup-missing-24h"
  namespace           = "AIERP/Backup"
  metric_name         = "BackupSuccess"
  statistic           = "Sum"
  period              = 86400
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  dimensions          = { Environment = var.environment }
  alarm_actions       = [var.alert_topic_arn]
  ok_actions          = [var.alert_topic_arn]
}

resource "aws_cloudwatch_metric_alarm" "restore_drill_overdue" {
  alarm_name          = "${local.name}-restore-drill-overdue-7d"
  namespace           = "AIERP/Backup"
  metric_name         = "RestoreDrillSuccess"
  statistic           = "Sum"
  period              = 86400
  evaluation_periods  = 7
  datapoints_to_alarm = 7
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  dimensions          = { Environment = var.environment }
  alarm_actions       = [var.alert_topic_arn]
  ok_actions          = [var.alert_topic_arn]
}

resource "aws_cloudwatch_log_metric_filter" "ai_provider_attempt" {
  name           = "${local.name}-ai-provider-attempt"
  pattern        = "ai_provider_attempt"
  log_group_name = aws_cloudwatch_log_group.ecs["ai"].name
  metric_transformation {
    name          = "ProviderAttempts"
    namespace     = "AIERP/AI"
    value         = "1"
    default_value = 0
  }
}

resource "aws_cloudwatch_log_metric_filter" "ai_provider_failure" {
  name           = "${local.name}-ai-provider-failure"
  pattern        = "ai_provider_failure"
  log_group_name = aws_cloudwatch_log_group.ecs["ai"].name
  metric_transformation {
    name          = "ProviderFailures"
    namespace     = "AIERP/AI"
    value         = "1"
    default_value = 0
  }
}

resource "aws_cloudwatch_metric_alarm" "ai_failure_rate" {
  alarm_name          = "${local.name}-ai-provider-failure-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 10
  treat_missing_data  = "notBreaching"
  alarm_actions       = [var.alert_topic_arn]
  ok_actions          = [var.alert_topic_arn]

  metric_query {
    id          = "rate"
    expression  = "IF(attempts>0,100*failures/attempts,0)"
    label       = "AI provider failure rate percent"
    return_data = true
  }
  metric_query {
    id          = "attempts"
    return_data = false
    metric {
      metric_name = "ProviderAttempts"
      namespace   = "AIERP/AI"
      period      = 300
      stat        = "Sum"
    }
  }
  metric_query {
    id          = "failures"
    return_data = false
    metric {
      metric_name = "ProviderFailures"
      namespace   = "AIERP/AI"
      period      = 300
      stat        = "Sum"
    }
  }
}
