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
        'resource "aws_nat_gateway"': "single balanced-pilot NAT egress",
        'resource "aws_wafv2_web_acl"': "WAF",
        'resource "aws_wafv2_web_acl_association"': "WAF association",
        'resource "aws_ecs_cluster"': "ECS cluster",
        'resource "aws_ecs_task_definition"': "ECS task definitions",
        'resource "aws_ecs_service"': "ECS services",
        'resource "aws_appautoscaling_target"': "bounded ECS autoscaling",
        "rollback = true": "deployment circuit breakers",
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
        "var.monthly_budget_usd == 600": "balanced-pilot USD 600 budget",
        "var.backup_retention_days == 14": "14-day managed backup retention",
        'num_cache_clusters = 1': "single-node balanced-pilot Valkey",
        'engine = "valkey"': "Valkey cache/queue engine",
        "@sha256:": "immutable example image references",
        'resource "aws_cloudwatch_metric_alarm" "ecs_running_tasks"': "ECS service-count alarms",
        'toset(["configure", "migrate", "backup", "restore"])': "on-demand configure/migrate/backup/restore tasks",
        '{ web = { name = aws_ecs_service.web.name, minimum = 1, maximum = 2 } }': "bounded web pilot scaling",
        '{ ai = { name = aws_ecs_service.ai.name, minimum = 1, maximum = 2 } }': "bounded AI pilot scaling",
    }
    for snippet, label in required.items():
        if snippet not in normalized:
            failures.append(f"AWS IaC missing invariant: {label}")

    forbidden_patterns = {
        r'resource\s+"aws_secretsmanager_secret_version"': "secret value in Terraform state",
        r'resource\s+"random_password"': "generated plaintext secret in Terraform state",
        r'(?i)\b(password|api_key|auth_token|shared_secret)\s*=\s*"[^"$<]': "plaintext secret assignment",
        r'(?i)terraform\s+apply': "apply automation in Terraform source",
    }
    for pattern, label in forbidden_patterns.items():
        if re.search(pattern, combined):
            failures.append(f"AWS IaC forbidden content: {label}")

    network = (TF_ROOT / "network.tf").read_text(encoding="utf-8")
    if len(re.findall(r'resource\s+"aws_nat_gateway"', network)) != 1 or "for_each = aws_subnet.public" in network:
        failures.append("AWS IaC balanced pilot must define exactly one NAT gateway without per-AZ for_each")

    image_contracts = [
        ROOT / "infra/images/frappe/backend.Dockerfile",
        ROOT / "infra/images/frappe/frontend.Dockerfile",
        ROOT / "infra/images/frappe/runtime.sh",
        ROOT / "services/ai_control_plane/Dockerfile.production",
    ]
    for path in image_contracts:
        if not path.is_file():
            failures.append(f"missing production image contract: {path.relative_to(ROOT)}")
    if all(path.is_file() for path in image_contracts):
        image_text = "\n".join(path.read_text(encoding="utf-8") for path in image_contracts)
        for marker in (
            "FRAPPE_BACKEND_BASE_IMAGE",
            "FRAPPE_FRONTEND_BASE_IMAGE",
            "PYTHON_BASE_IMAGE",
            "USER 1000:1000",
            "USER 10001:10001",
            "HEALTHCHECK",
            "http://127.0.0.1:8090/healthz",
        ):
            if marker not in image_text:
                failures.append(f"production image contract missing marker: {marker}")

    if failures:
        print("AWS production IaC check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("AWS production IaC check passed (static, plan-only, no AWS calls).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
