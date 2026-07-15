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


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check-terraform-plan.py <terraform-show.json>", file=sys.stderr)
        return 64
    path = Path(sys.argv[1])
    plan = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    counts: dict[str, int] = {}

    for change in plan.get("resource_changes", []):
        address = str(change.get("address", ""))
        resource_type = str(change.get("type", ""))
        actions = change.get("change", {}).get("actions", [])
        for action in actions:
            counts[action] = counts.get(action, 0) + 1
        if "delete" in actions:
            failures.append(f"destructive action is not allowed: {address} -> {actions}")
        if resource_type and not resource_type.startswith(ALLOWED_PREFIXES):
            failures.append(f"resource provider is outside the AWS pilot scope: {address}")
        after = change.get("change", {}).get("after")
        if isinstance(after, dict) and "secret_string" in after:
            failures.append(f"secret material would enter Terraform state: {address}")

    output = {
        "format_version": plan.get("format_version"),
        "terraform_version": plan.get("terraform_version"),
        "resource_change_actions": counts,
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
