locals {
  name = "ai-erp-${var.environment}"
  tags = {
    Project       = "AI ERP Demo"
    Environment   = var.environment
    ManagedBy     = "Terraform"
    DataResidency = "EU"
    Owner         = var.owner
  }
}
