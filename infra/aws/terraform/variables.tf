variable "aws_region" {
  description = "Approved AWS region. The first production pilot is EU-only."
  type        = string
  default     = "eu-central-1"

  validation {
    condition     = var.aws_region == "eu-central-1"
    error_message = "The approved pilot region is eu-central-1."
  }
}

variable "environment" {
  description = "Short environment identifier used in names and tags."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,14}$", var.environment))
    error_message = "environment must be 2-15 lowercase letters, digits, or hyphens."
  }
}

variable "aws_account_id" {
  description = "Approved 12-digit AWS account ID; keep real values in private tfvars."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must contain exactly 12 digits."
  }
}

variable "availability_zones" {
  description = "Exactly two eu-central-1 availability zones."
  type        = list(string)

  validation {
    condition = (
      length(var.availability_zones) == 2 &&
      length(distinct(var.availability_zones)) == 2 &&
      alltrue([for zone in var.availability_zones : startswith(zone, "eu-central-1")])
    )
    error_message = "Provide two distinct eu-central-1 availability zones."
  }
}

variable "vpc_cidr" {
  type        = string
  description = "Private VPC CIDR."
  default     = "10.40.0.0/16"
}

variable "public_subnet_cidrs" {
  type        = list(string)
  description = "Two public subnet CIDRs, ordered like availability_zones."

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Provide exactly two public subnet CIDRs."
  }
}

variable "private_subnet_cidrs" {
  type        = list(string)
  description = "Two private workload/data subnet CIDRs."

  validation {
    condition     = length(var.private_subnet_cidrs) == 2
    error_message = "Provide exactly two private subnet CIDRs."
  }
}

variable "domain_name" {
  type        = string
  description = "Approved production hostname; must already be under owner control."

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]+[a-z0-9]$", var.domain_name))
    error_message = "domain_name must be a valid lowercase hostname."
  }
}

variable "certificate_arn" {
  type        = string
  description = "ARN of an approved ACM certificate in eu-central-1."

  validation {
    condition     = can(regex("^arn:aws:acm:eu-central-1:[0-9]{12}:certificate/", var.certificate_arn))
    error_message = "certificate_arn must identify an eu-central-1 ACM certificate."
  }
}

variable "monthly_budget_usd" {
  type        = number
  description = "Owner-approved numeric monthly AWS cost budget in USD."

  validation {
    condition     = var.monthly_budget_usd >= 100 && var.monthly_budget_usd <= 100000
    error_message = "monthly_budget_usd must be an explicitly approved value from 100 to 100000."
  }
}

variable "backup_retention_days" {
  type        = number
  description = "Owner-approved RDS and Redis recovery retention in days."

  validation {
    condition     = var.backup_retention_days >= 7 && var.backup_retention_days <= 35
    error_message = "backup_retention_days must be between 7 and 35."
  }
}

variable "logical_backup_retention_days" {
  type        = number
  description = "Owner-approved versioned logical-backup retention in days."

  validation {
    condition     = var.logical_backup_retention_days >= 30 && var.logical_backup_retention_days <= 2555
    error_message = "logical_backup_retention_days must be between 30 days and 7 years."
  }
}

variable "log_retention_days" {
  type        = number
  description = "Approved CloudWatch retention."

  validation {
    condition     = contains([30, 60, 90, 120, 150, 180, 365, 400, 545, 731], var.log_retention_days)
    error_message = "Use an AWS-supported approved retention value."
  }
}

variable "db_instance_class" {
  type        = string
  description = "Cost-reviewed RDS instance class."
  default     = "db.t4g.medium"
}

variable "redis_node_type" {
  type        = string
  description = "Cost-reviewed ElastiCache node type."
  default     = "cache.t4g.small"
}

variable "waf_rate_limit" {
  type        = number
  description = "Five-minute per-IP WAF request threshold."
  default     = 2000

  validation {
    condition     = var.waf_rate_limit >= 100 && var.waf_rate_limit <= 20000
    error_message = "waf_rate_limit must be between 100 and 20000."
  }
}

variable "owner" {
  type        = string
  description = "Named operational owner; a role name is acceptable."

  validation {
    condition     = length(trimspace(var.owner)) >= 3
    error_message = "A named operational owner is required."
  }
}
