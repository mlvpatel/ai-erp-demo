terraform {
  required_version = "= 1.13.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.51.0"
    }
  }

  # Configure the private, encrypted state bucket with S3 lockfiles only
  # through protected workflow inputs after the ADR-0007 gate is approved.
  backend "s3" {}
}
