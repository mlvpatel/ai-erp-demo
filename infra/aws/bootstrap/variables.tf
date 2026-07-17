variable "aws_region" {
  type        = string
  description = "Approved AWS region."
  default     = "eu-central-1"

  validation {
    condition     = var.aws_region == "eu-central-1"
    error_message = "The production bootstrap is restricted to eu-central-1."
  }
}

variable "aws_account_id" {
  type        = string
  description = "Approved AWS account ID. Keep the real value in an untracked tfvars file."

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must contain exactly 12 digits."
  }
}

variable "github_repository" {
  type        = string
  description = "Repository allowed to assume the protected GitHub environment roles."
  default     = "mlvpatel/ai-erp-demo"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must be an owner/repository pair."
  }
}

variable "github_environment" {
  type        = string
  description = "Protected GitHub environment included in the OIDC subject."
  default     = "production"

  validation {
    condition     = var.github_environment == "production"
    error_message = "The first release uses the protected production environment."
  }
}
