#!/usr/bin/env python3
"""Static, credential-free invariants for the plan-only AWS foundation."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TF_ROOT = ROOT / "infra" / "aws" / "terraform"


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def main() -> int:
    failures: list[str] = []
    required_files = {
        "README.md",
        "versions.tf",
        "providers.tf",
        "variables.tf",
        "locals.tf",
        "network.tf",
        "security.tf",
        "data.tf",
        "compute.tf",
        "edge.tf",
        "observability.tf",
        "outputs.tf",
        "terraform.tfvars.example",
    }
    present = {path.name for path in TF_ROOT.iterdir()} if TF_ROOT.is_dir() else set()
    for name in sorted(required_files - present):
        failures.append(f"missing AWS IaC file: infra/aws/terraform/{name}")

    tf_files = sorted(TF_ROOT.glob("*.tf"))
    combined = "\n".join(path.read_text(encoding="utf-8") for path in tf_files)
    normalized = compact(combined)

    required = {
        'required_version = "= 1.13.5"': "pinned Terraform version",
        'version = "= 6.51.0"': "pinned AWS provider",
        'limit_unit = "USD"': "AWS cost-budget unit",
        'default = "eu-central-1"': "EU region default",
        'var.aws_region == "eu-central-1"': "EU region validation",
        'resource "aws_nat_gateway"': "two-AZ private egress",
        'resource "aws_wafv2_web_acl"': "WAF",
        'resource "aws_wafv2_web_acl_association"': "WAF association",
        'resource "aws_ecs_cluster"': "ECS cluster",
        'value = "enhanced"': "enhanced container insights",
        'engine = "mariadb"': "MariaDB",
        "manage_master_user_password = true": "AWS-managed database password",
        "multi_az = true": "database Multi-AZ",
        "publicly_accessible = false": "private database",
        "deletion_protection = true": "database/ALB deletion protection",
        "at_rest_encryption_enabled = true": "Redis at-rest encryption",
        "transit_encryption_enabled = true": "Redis transport encryption",
        'resource "aws_efs_backup_policy"': "EFS backups",
        'object_ownership = "BucketOwnerEnforced"': "S3 ownership enforcement",
        'sse_algorithm = "aws:kms"': "S3 KMS encryption",
        'variable = "aws:SecureTransport"': "S3 TLS policy",
        'resource "aws_budgets_budget"': "numeric budget",
        'message_body = "Service deployment pending"': "empty edge fail-closed response",
    }
    for snippet, label in required.items():
        if snippet not in normalized:
            failures.append(f"AWS IaC missing invariant: {label}")

    forbidden_patterns = {
        r'resource\s+"aws_ecs_(?:task_definition|service)"': "workload service before image contract",
        r'resource\s+"aws_secretsmanager_secret_version"': "secret value in Terraform state",
        r'resource\s+"random_password"': "generated plaintext secret in Terraform state",
        r'(?i)\b(password|api_key|auth_token|shared_secret)\s*=\s*"[^"$<]': "plaintext secret assignment",
        r'(?i)terraform\s+apply': "apply automation in Terraform source",
    }
    for pattern, label in forbidden_patterns.items():
        if re.search(pattern, combined):
            failures.append(f"AWS IaC forbidden content: {label}")

    if failures:
        print("AWS production IaC check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("AWS production IaC check passed (static, plan-only, no AWS calls).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
