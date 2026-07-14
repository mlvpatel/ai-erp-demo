terraform {
  required_version = "= 1.13.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.51.0"
    }
  }

  # Configure the private, encrypted state bucket and lock table only through
  # an untracked backend config after the ADR-0007 apply gate is approved.
  backend "s3" {}
}
