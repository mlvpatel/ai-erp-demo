#!/usr/bin/env python3
"""Validate that public API and event contracts are cataloged."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG = REPO_ROOT / "contracts" / "catalog.json"
CONTRACT_ROOTS = (
    REPO_ROOT / "contracts" / "openapi",
    REPO_ROOT / "contracts" / "events",
)

ALLOWED_KINDS = {"openapi", "business-event"}
ALLOWED_STATUSES = {"implemented", "contract-only", "planned"}
REQUIRED_FIELDS = {
    "id",
    "kind",
    "status",
    "version",
    "path",
    "owner_area",
    "producer",
    "consumers",
    "safety_boundary",
    "tests",
    "verification",
}
REQUIRED_SAFETY_TERMS = {
    "mutation",
    "money",
    "stock",
    "payroll",
    "permission",
    "compliance",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require_non_empty_list(
    failures: list[str], contract_id: str, contract: dict[str, Any], field: str
) -> list[str]:
    value = contract.get(field)
    if not isinstance(value, list) or not value:
        fail(failures, f"{contract_id}: {field} must be a non-empty list")
        return []
    if any(not isinstance(item, str) or not item.strip() for item in value):
        fail(failures, f"{contract_id}: {field} must contain non-empty strings")
        return []
    return value


def discover_contract_files() -> set[str]:
    files: set[str] = set()
    for root in CONTRACT_ROOTS:
        for path in root.glob("*.yaml"):
            files.add(rel(path))
    return files


def validate_contract(failures: list[str], contract: Any) -> tuple[str | None, str | None]:
    if not isinstance(contract, dict):
        fail(failures, "each catalog entry must be an object")
        return None, None

    contract_id = str(contract.get("id", "<missing-id>"))
    missing = sorted(REQUIRED_FIELDS - set(contract))
    if missing:
        fail(failures, f"{contract_id}: missing required fields: {', '.join(missing)}")

    for field in ("id", "version", "path", "owner_area", "producer", "safety_boundary"):
        if not isinstance(contract.get(field), str) or not contract[field].strip():
            fail(failures, f"{contract_id}: {field} must be a non-empty string")

    kind = contract.get("kind")
    if kind not in ALLOWED_KINDS:
        fail(failures, f"{contract_id}: kind must be one of {', '.join(sorted(ALLOWED_KINDS))}")

    status = contract.get("status")
    if status not in ALLOWED_STATUSES:
        fail(
            failures,
            f"{contract_id}: status must be one of {', '.join(sorted(ALLOWED_STATUSES))}",
        )

    path_value = contract.get("path")
    contract_path: Path | None = None
    if isinstance(path_value, str):
        contract_path = REPO_ROOT / path_value
        if not contract_path.is_file():
            fail(failures, f"{contract_id}: contract path does not exist: {path_value}")
        elif not path_value.startswith("contracts/openapi/") and not path_value.startswith("contracts/events/"):
            fail(failures, f"{contract_id}: contract path must be under contracts/openapi or contracts/events")

    owner_area = contract.get("owner_area")
    if isinstance(owner_area, str) and not (REPO_ROOT / owner_area).exists():
        fail(failures, f"{contract_id}: owner_area does not exist: {owner_area}")

    consumers = require_non_empty_list(failures, contract_id, contract, "consumers")
    for consumer in consumers:
        if not (REPO_ROOT / consumer).exists():
            fail(failures, f"{contract_id}: consumer path does not exist: {consumer}")

    tests = require_non_empty_list(failures, contract_id, contract, "tests")
    for test_path in tests:
        test_file = REPO_ROOT / test_path
        if not test_file.is_file():
            fail(failures, f"{contract_id}: test path does not exist: {test_path}")
        elif isinstance(path_value, str) and Path(path_value).name not in text(test_file):
            fail(failures, f"{contract_id}: test {test_path} must reference {Path(path_value).name}")

    verification = require_non_empty_list(failures, contract_id, contract, "verification")
    if status == "implemented" and not any(item.startswith("scripts/dev.sh ") for item in verification):
        fail(failures, f"{contract_id}: implemented contract needs a scripts/dev.sh verification command")

    safety_boundary = str(contract.get("safety_boundary", "")).lower()
    for term in REQUIRED_SAFETY_TERMS:
        if term not in safety_boundary:
            fail(failures, f"{contract_id}: safety_boundary must mention {term}")

    if contract_path and contract_path.exists():
        contract_text = text(contract_path)
        if kind == "openapi":
            if "openapi:" not in contract_text or "version:" not in contract_text:
                fail(failures, f"{contract_id}: OpenAPI contract must declare openapi and version")
            if "draft_only" not in contract_text or "allowed_action" not in contract_text:
                fail(failures, f"{contract_id}: OpenAPI AI boundary must remain draft-only with allowed_action")
        if kind == "business-event":
            if "schema_version:" not in contract_text or "event_types:" not in contract_text:
                fail(failures, f"{contract_id}: event contract must declare schema_version and event_types")
            if status == "contract-only" and "status: contract-only" not in contract_text:
                fail(failures, f"{contract_id}: contract-only status must be visible in event contract")
            if not re.search(r"\.v\d+\b", contract_text):
                fail(failures, f"{contract_id}: event types must be explicitly versioned")

    return contract_id if isinstance(contract.get("id"), str) else None, path_value if isinstance(path_value, str) else None


def main() -> int:
    failures: list[str] = []

    try:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"FAIL: missing contract catalog: {rel(CATALOG)}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"FAIL: invalid JSON in {rel(CATALOG)}: {exc}", file=sys.stderr)
        return 1

    if catalog.get("schema_version") != 1:
        fail(failures, "catalog schema_version must be 1")

    contracts = catalog.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        fail(failures, "contracts must be a non-empty list")
        contracts = []

    seen_ids: set[str] = set()
    cataloged_paths: set[str] = set()

    for contract in contracts:
        contract_id, path_value = validate_contract(failures, contract)
        if contract_id:
            if contract_id in seen_ids:
                fail(failures, f"{contract_id}: duplicate contract id")
            seen_ids.add(contract_id)
        if path_value:
            if path_value in cataloged_paths:
                fail(failures, f"{path_value}: duplicate contract path")
            cataloged_paths.add(path_value)

    discovered = discover_contract_files()
    missing_from_catalog = sorted(discovered - cataloged_paths)
    extra_in_catalog = sorted(cataloged_paths - discovered)
    if missing_from_catalog:
        fail(failures, f"contract files missing from catalog: {', '.join(missing_from_catalog)}")
    if extra_in_catalog:
        fail(failures, f"catalog paths do not exist as contract files: {', '.join(extra_in_catalog)}")

    if failures:
        print("Contract catalog check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Contract catalog check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
