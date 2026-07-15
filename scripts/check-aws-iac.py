#!/usr/bin/env python3
"""Static, credential-free invariants for the plan-only AWS foundation."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TF_ROOT = ROOT / "infra" / "aws" / "terraform"
BOOTSTRAP_ROOT = ROOT / "infra" / "aws" / "bootstrap"


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

    bootstrap_files = {
        "README.md",
        "versions.tf",
        "variables.tf",
        "main.tf",
        "outputs.tf",
        "terraform.tfvars.example",
        ".terraform.lock.hcl",
    }
    bootstrap_present = (
        {path.name for path in BOOTSTRAP_ROOT.iterdir()} if BOOTSTRAP_ROOT.is_dir() else set()
    )
    for name in sorted(bootstrap_files - bootstrap_present):
        failures.append(f"missing AWS bootstrap file: infra/aws/bootstrap/{name}")

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
        'resource "aws_cloudwatch_metric_alarm" "backup_freshness"': "24-hour backup freshness alarm",
        'resource "aws_cloudwatch_metric_alarm" "restore_drill_overdue"': "restore drill freshness alarm",
        'resource "aws_cloudwatch_metric_alarm" "ai_failure_rate"': "AI provider failure-rate alarm",
        'pattern = "ai_provider_failure"': "payload-free AI provider failure metric",
        'subscriber_sns_topic_arns = [var.alert_topic_arn]': "50/80/100 budget alert delivery",
        'for_each = toset([50, 80, 100])': "budget thresholds at 50, 80, and 100 percent",
        'notification_type = "ACTUAL"': "actual budget alert thresholds",
        'resource "aws_cloudwatch_event_rule" "daily_backup"': "scheduled daily backup",
        'state = var.activate_services ? "ENABLED" : "DISABLED"': "post-activation backup scheduling",
        'alarm_actions = [var.alert_topic_arn]': "operational alert delivery",
        'toset(["configure", "migrate", "backup", "restore"])': "on-demand configure/migrate/backup/restore tasks",
        'resource "aws_ecs_task_definition" "ai_live_eval"': "private one-case OpenAI evaluation task",
        'resource "aws_ecs_task_definition" "capacity"': "disposable full-profile capacity task",
        'I_ACKNOWLEDGE_DISPOSABLE_SYNTHETIC_CAPACITY': "explicit synthetic capacity gate",
        'I_ACKNOWLEDGE_SYNTHETIC_ONLY': "explicit synthetic live-evaluation gate",
        'minimum = var.activate_services ? 1 : 0, maximum = 2': "inactive-until-configured web and AI scaling",
        'desired_count = var.activate_services ? 1 : 0': "inactive-until-configured long-running services",
        'valueFrom = "${aws_secretsmanager_secret.frappe.arn}:admin_password::"': "secret-injected site bootstrap",
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

    bootstrap_tf = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(BOOTSTRAP_ROOT.glob("*.tf"))
    )
    bootstrap_required = {
        'required_version = "= 1.13.5"': "pinned bootstrap Terraform version",
        'version = "= 6.51.0"': "pinned bootstrap AWS provider",
        'repo:${var.github_repository}:environment:${var.github_environment}': "environment-scoped GitHub OIDC subject",
        'image_tag_mutability = "IMMUTABLE"': "immutable ECR repositories",
        'scan_on_push = true': "ECR scan-on-push",
        'customer_master_key_spec = "RSA_4096"': "asymmetric KMS signing key",
        'prevent_destroy = true': "protected bootstrap state resources",
        'variable = "aws:SecureTransport"': "bootstrap S3 TLS-only policies",
        'resource "aws_s3_bucket_policy" "state_logs"': "separate state-log bucket policy",
        'data "aws_iam_policy_document" "state_logs"': "state-log policy document",
        'actions = ["sts:AssumeRoleWithWebIdentity"]': "OIDC-only GitHub role assumption",
        'policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"': "separate protected deploy role",
        'sid = "NamedPilotRoles"': "name-scoped IAM deployment permission",
    }
    for snippet, label in bootstrap_required.items():
        if snippet not in compact(bootstrap_tf):
            failures.append(f"AWS bootstrap missing invariant: {label}")
    for pattern, label in forbidden_patterns.items():
        if re.search(pattern, bootstrap_tf):
            failures.append(f"AWS bootstrap forbidden content: {label}")

    image_workflow_path = ROOT / ".github" / "workflows" / "production-images.yml"
    if not image_workflow_path.is_file():
        failures.append("missing production image publication workflow")
    else:
        image_workflow = image_workflow_path.read_text(encoding="utf-8")
        workflow_markers = {
            "workflow_dispatch:": "manual image release trigger",
            "environment: production": "protected production environment",
            "id-token: write": "GitHub OIDC permission",
            "github.ref == 'refs/heads/main'": "main-only image release",
            "@sha256:": "digest-pinned build base validation",
            "provenance: mode=max": "BuildKit provenance",
            "sbom: true": "BuildKit SBOM attestation",
            "scanners: vuln,secret": "vulnerability and secret scanning",
            "format: cyclonedx": "CycloneDX evidence",
            "cosign sign --yes --key": "KMS image signature",
            "cosign verify --key": "signature verification",
            "retention-days: 30": "bounded private evidence retention",
        }
        for snippet, label in workflow_markers.items():
            if snippet not in image_workflow:
                failures.append(f"production image workflow missing invariant: {label}")
        for line_number, line in enumerate(image_workflow.splitlines(), 1):
            action = re.search(r"\buses:\s*([^\s#]+)", line)
            if action and not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", action.group(1)):
                failures.append(
                    "production image workflow action must be pinned to a full commit SHA "
                    f"at line {line_number}"
                )

    for lock_path in (
        ROOT / "services" / "ai_control_plane" / "uv.lock",
        ROOT / "services" / "ai_control_plane" / "requirements.lock",
    ):
        if not lock_path.is_file() or not lock_path.read_text(encoding="utf-8").strip():
            failures.append(f"missing AI production dependency lock: {lock_path.relative_to(ROOT)}")

    delivery_workflow_path = ROOT / ".github" / "workflows" / "production-deploy.yml"
    if not delivery_workflow_path.is_file():
        failures.append("missing protected production delivery workflow")
    else:
        delivery_workflow = delivery_workflow_path.read_text(encoding="utf-8")
        delivery_markers = {
            "workflow_dispatch:": "manual delivery trigger",
            "environment: production": "protected deployment environment",
            "id-token: write": "deployment OIDC permission",
            "github.ref == 'refs/heads/main'": "main-only deployment",
            "APPLY-AI-ERP-PILOT": "explicit apply confirmation",
            "ROLLBACK-AI-ERP-PILOT": "explicit rollback confirmation",
            "use_lockfile=true": "remote state locking",
            "scripts/check-terraform-plan.py": "plan policy check",
            "cosign verify --key": "promotion signature verification",
            "scripts/run-ecs-operation.sh configure": "fresh-site configuration",
            "scripts/run-ecs-operation.sh migrate": "controlled migration",
            "scripts/run-ecs-operation.sh backup": "first verified logical backup",
            "scripts/run-ai-live-eval.sh": "private synthetic provider evaluation",
            "activate_services=true": "post-migration activation",
            "aws ecs wait services-stable": "service stability gate",
            "https://${DOMAIN_NAME}/api/method/ping": "TLS application smoke test",
        }
        for snippet, label in delivery_markers.items():
            if snippet not in delivery_workflow:
                failures.append(f"production delivery workflow missing invariant: {label}")
        for line_number, line in enumerate(delivery_workflow.splitlines(), 1):
            action = re.search(r"\buses:\s*([^\s#]+)", line)
            if action and not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", action.group(1)):
                failures.append(
                    "production delivery workflow action must be pinned to a full commit SHA "
                    f"at line {line_number}"
                )

    for helper in (
        ROOT / "scripts" / "check-terraform-plan.py",
        ROOT / "scripts" / "run-ecs-operation.sh",
        ROOT / "scripts" / "run-ai-live-eval.sh",
        ROOT / "scripts" / "run-restore-drill.sh",
        ROOT / "scripts" / "run-full-capacity.sh",
        ROOT / "scripts" / "check-capacity-evidence.py",
    ):
        if not helper.is_file():
            failures.append(f"missing production delivery helper: {helper.relative_to(ROOT)}")

    restore_workflow_path = ROOT / ".github" / "workflows" / "production-restore-drill.yml"
    if not restore_workflow_path.is_file():
        failures.append("missing protected restore and deletion drill workflow")
    else:
        restore_workflow = restore_workflow_path.read_text(encoding="utf-8")
        restore_markers = {
            "workflow_dispatch:": "manual restore-drill trigger",
            "environment: production": "protected restore environment",
            "RESTORE-DELETE-DRILL": "explicit restore authorization",
            "github.ref == 'refs/heads/main'": "main-only restore drill",
            "scripts/run-restore-drill.sh": "disposable restore runner",
            "use_lockfile=true": "locked remote state read",
            "retention-days: 30": "bounded private restore evidence",
        }
        for snippet, label in restore_markers.items():
            if snippet not in restore_workflow:
                failures.append(f"restore workflow missing invariant: {label}")
        for line_number, line in enumerate(restore_workflow.splitlines(), 1):
            action = re.search(r"\buses:\s*([^\s#]+)", line)
            if action and not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", action.group(1)):
                failures.append(
                    "restore workflow action must be pinned to a full commit SHA "
                    f"at line {line_number}"
                )

    capacity_workflow_path = ROOT / ".github" / "workflows" / "production-capacity.yml"
    if not capacity_workflow_path.is_file():
        failures.append("missing protected full capacity workflow")
    else:
        capacity_workflow = capacity_workflow_path.read_text(encoding="utf-8")
        capacity_markers = {
            "workflow_dispatch:": "manual capacity trigger",
            "environment: production": "protected capacity environment",
            "RUN-FULL-CAPACITY": "explicit capacity authorization",
            "github.ref == 'refs/heads/main'": "main-only capacity run",
            "scripts/run-full-capacity.sh": "disposable capacity runner",
            "use_lockfile=true": "locked remote state read",
            "retention-days: 30": "bounded private capacity evidence",
        }
        for snippet, label in capacity_markers.items():
            if snippet not in capacity_workflow:
                failures.append(f"capacity workflow missing invariant: {label}")
        for line_number, line in enumerate(capacity_workflow.splitlines(), 1):
            action = re.search(r"\buses:\s*([^\s#]+)", line)
            if action and not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", action.group(1)):
                failures.append(
                    "capacity workflow action must be pinned to a full commit SHA "
                    f"at line {line_number}"
                )

    network = (TF_ROOT / "network.tf").read_text(encoding="utf-8")
    if len(re.findall(r'resource\s+"aws_nat_gateway"', network)) != 1 or "for_each = aws_subnet.public" in network:
        failures.append("AWS IaC balanced pilot must define exactly one NAT gateway without per-AZ for_each")

    image_contracts = [
        ROOT / "infra/images/frappe/backend.Dockerfile",
        ROOT / "infra/images/frappe/frontend.Dockerfile",
        ROOT / "infra/images/frappe/runtime.sh",
        ROOT / "infra/images/frappe/backup_to_s3.py",
        ROOT / "infra/images/frappe/restore_drill.py",
        ROOT / "infra/images/frappe/capacity_run.py",
        ROOT / "infra/images/frappe/requirements-ops.lock",
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
            "ensure_apps_registry",
            "bench new-site",
            "--install-app ai_erp_service",
            "backup-to-s3",
            "--require-hashes",
            "BackupSuccess",
            "I_ACKNOWLEDGE_DISPOSABLE_RESTORE",
            "restore_validation.validate_restore",
            "I_ACKNOWLEDGE_DISPOSABLE_SYNTHETIC_CAPACITY",
            "ai_erp_service.capacity.run",
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
