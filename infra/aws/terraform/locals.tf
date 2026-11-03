locals {
  name     = "ai-erp-${var.environment}"
  vpc_cidr = "10.40.0.0/16"
  tags = {
    Project       = "AI ERP Demo"
    Environment   = var.environment
    ManagedBy     = "Terraform"
    DataResidency = "EU"
    Owner         = var.owner
  }
}
