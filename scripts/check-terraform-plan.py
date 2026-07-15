#!/usr/bin/env python3
"""Fail closed on destructive or out-of-scope production Terraform plans."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ALLOWED_PREFIXES = (
    "aws_",
    "data.aws_",
)
REPLACEABLE_RESOURCE_TYPES = frozenset(
    {
        "aws_appautoscaling_policy",
        "aws_appautoscaling_target",
        "aws_cloudwatch_log_metric_filter",
        "aws_cloudwatch_metric_alarm",
        "aws_ecs_service",
        "aws_ecs_task_definition",
        "aws_iam_role_policy",
        "aws_scheduler_schedule",
    }
)
PROTECTED_RESOURCE_TYPES = frozenset(
    {
        "aws_db_instance",
        "aws_efs_file_system",
        "aws_kms_alias",
        "aws_kms_key",
        "aws_s3_bucket",
        "aws_secretsmanager_secret",
        "aws_secretsmanager_secret_version",
        "aws_subnet",
        "aws_vpc",
    }
)


def contains_secret_material(value: object) -> bool:
    if isinstance(value, dict):
        return any(key == "secret_string" or contains_secret_material(item) for key, item in value.items())
    if isinstance(value, list):
        return any(contains_secret_material(item) for item in value)
    return False


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check-terraform-plan.py <terraform-show.json>", file=sys.stderr)
        return 64
    path = Path(sys.argv[1])
    plan = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    counts: dict[str, int] = {}
    replacements = 0

    for change in plan.get("resource_changes", []):
        address = str(change.get("address", ""))
        resource_type = str(change.get("type", ""))
        actions = change.get("change", {}).get("actions", [])
        for action in actions:
            counts[action] = counts.get(action, 0) + 1
        action_set = set(actions)
        if action_set == {"delete"}:
            failures.append(f"delete-only action is not allowed: {address} -> {actions}")
        elif "delete" in action_set:
            replacements += 1
            if resource_type in PROTECTED_RESOURCE_TYPES:
                failures.append(f"protected resource replacement is not allowed: {address} -> {actions}")
            elif resource_type not in REPLACEABLE_RESOURCE_TYPES:
                failures.append(f"resource replacement is not allow-listed: {address} -> {actions}")
        if resource_type and not resource_type.startswith(ALLOWED_PREFIXES):
            failures.append(f"resource provider is outside the AWS pilot scope: {address}")
        after = change.get("change", {}).get("after")
        if contains_secret_material(after):
            failures.append(f"secret material would enter Terraform state: {address}")

    output = {
        "format_version": plan.get("format_version"),
        "terraform_version": plan.get("terraform_version"),
        "resource_change_actions": counts,
        "reviewed_replacements": replacements,
        "destructive_changes": 0,
    }
    print(json.dumps(output, sort_keys=True))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
