#!/usr/bin/env python3
"""Validate downloaded aggregate capacity evidence before release retention."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EXPECTED_COUNTS = {
    "customers": 250,
    "service_locations": 500,
    "items": 750,
    "service_requests": 1000,
    "service_work_orders": 5000,
    "service_work_order_time_rows": 10000,
    "service_work_order_part_rows": 10000,
    "ai_proposals": 1000,
    "stock_entries": 2000,
    "draft_sales_invoices": 1000,
}


def validate(path: Path) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != 1 or value.get("status") != "PASS":
        raise ValueError("evidence is not a passing v1 result")
    if value.get("full_profile") is not True or value.get("synthetic_only") is not True:
        raise ValueError("evidence is not a synthetic full profile")
    if value.get("record_counts") != EXPECTED_COUNTS:
        raise ValueError("record counts do not match the approved profile")
    results = value.get("results")
    if not isinstance(results, list) or len(results) != 7 or any(item.get("status") != "PASS" for item in results):
        raise ValueError("scenario results are incomplete")
    concurrency = value.get("concurrency")
    if concurrency != {
        "request_count": 10,
        "authenticated_sessions": 10,
        "distinct_users": 5,
        "stock_entries_created": 1,
        "unique_result_count": 1,
        "partial_issue": False,
        "retry_idempotent": True,
    }:
        raise ValueError("concurrency result is invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", value.get("commit", "")):
        raise ValueError("release commit is invalid")
    if not str(value.get("workflow_run", "")).isdigit():
        raise ValueError("workflow run is invalid")


def main() -> int:
    try:
        if len(sys.argv) != 2:
            raise ValueError("one evidence path is required")
        validate(Path(sys.argv[1]))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"capacity evidence validation failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print("capacity evidence validation passed (aggregate synthetic data only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
