#!/usr/bin/env python3
"""Validate the industry-pack manifest.

The manifest is intentionally JSON so this check can run with only the Python
standard library. It keeps the "many industries" roadmap explicit without
claiming unfinished packs are implemented.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "config" / "industry-packs.json"

ALLOWED_STATUSES = {"implemented", "configured_demo", "reserved", "planned"}
REQUIRED_FIELDS = {
    "id",
    "order",
    "title",
    "status",
    "app_path",
    "docs",
    "entry_gate",
    "first_proof_workflow",
    "erpnext_reuse",
    "ai_allowed",
    "ai_forbidden",
    "verification",
}
REQUIRED_AI_FORBIDDEN_TERMS = {
    "financial",
    "inventory",
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


def require_non_empty_list(
    failures: list[str], pack_id: str, pack: dict[str, Any], field: str
) -> list[Any]:
    value = pack.get(field)
    if not isinstance(value, list) or not value:
        fail(failures, f"{pack_id}: {field} must be a non-empty list")
        return []
    if any(not isinstance(item, str) or not item.strip() for item in value):
        fail(failures, f"{pack_id}: {field} must contain non-empty strings only")
    return value


def validate_pack(failures: list[str], pack: Any) -> tuple[str | None, int | None]:
    if not isinstance(pack, dict):
        fail(failures, "each industry pack entry must be an object")
        return None, None

    pack_id = str(pack.get("id", "<missing-id>"))
    missing = sorted(REQUIRED_FIELDS - set(pack))
    if missing:
        fail(failures, f"{pack_id}: missing required fields: {', '.join(missing)}")

    if not isinstance(pack.get("id"), str) or not pack["id"].strip():
        fail(failures, f"{pack_id}: id must be a non-empty string")
        pack_id = None

    order = pack.get("order")
    if not isinstance(order, int) or order < 1:
        fail(failures, f"{pack_id}: order must be a positive integer")
        order = None

    for field in ("title", "entry_gate", "first_proof_workflow"):
        if not isinstance(pack.get(field), str) or not pack[field].strip():
            fail(failures, f"{pack_id}: {field} must be a non-empty string")

    status = pack.get("status")
    if status not in ALLOWED_STATUSES:
        fail(
            failures,
            f"{pack_id}: status must be one of {', '.join(sorted(ALLOWED_STATUSES))}",
        )

    docs = require_non_empty_list(failures, str(pack_id), pack, "docs")
    for doc in docs:
        doc_path = REPO_ROOT / doc
        if not doc_path.exists():
            fail(failures, f"{pack_id}: documentation path does not exist: {doc}")

    require_non_empty_list(failures, str(pack_id), pack, "erpnext_reuse")
    require_non_empty_list(failures, str(pack_id), pack, "ai_allowed")
    require_non_empty_list(failures, str(pack_id), pack, "verification")
    ai_forbidden = require_non_empty_list(failures, str(pack_id), pack, "ai_forbidden")
    forbidden_text = " ".join(ai_forbidden).lower()
    for term in REQUIRED_AI_FORBIDDEN_TERMS:
        if term not in forbidden_text:
            fail(failures, f"{pack_id}: ai_forbidden must mention {term}")

    app_path_value = pack.get("app_path")
    if status in {"implemented", "configured_demo", "reserved"}:
        if not isinstance(app_path_value, str) or not app_path_value.strip():
            fail(failures, f"{pack_id}: {status} packs must set app_path")
        else:
            app_path = REPO_ROOT / app_path_value
            if not app_path.is_dir():
                fail(failures, f"{pack_id}: app_path is not a directory: {app_path_value}")
            if not (app_path / "README.md").is_file():
                fail(failures, f"{pack_id}: app_path must contain README.md: {app_path_value}")
            if status in {"reserved", "configured_demo"} and (app_path / "pyproject.toml").exists():
                fail(
                    failures,
                    f"{pack_id}: documentation-only pack already looks generated: {rel(app_path / 'pyproject.toml')}",
                )
    elif status == "planned" and app_path_value is not None:
        fail(failures, f"{pack_id}: planned packs must leave app_path as null")

    if status == "implemented":
        verification = pack.get("verification", [])
        if not any(str(item).startswith("scripts/dev.sh ") for item in verification):
            fail(failures, f"{pack_id}: implemented packs need a scripts/dev.sh verification command")
    elif status == "configured_demo":
        demo_manifest = pack.get("demo_manifest")
        if not isinstance(demo_manifest, str) or not demo_manifest.startswith("config/industry-demo-"):
            fail(failures, f"{pack_id}: configured_demo requires a config/industry-demo-* manifest")
        elif not (REPO_ROOT / demo_manifest).is_file():
            fail(failures, f"{pack_id}: configured demo manifest is missing: {demo_manifest}")

    return pack_id, order


def main() -> int:
    failures: list[str] = []

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"FAIL: missing manifest: {rel(MANIFEST)}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"FAIL: invalid JSON in {rel(MANIFEST)}: {exc}", file=sys.stderr)
        return 1

    if manifest.get("schema_version") != 1:
        fail(failures, "schema_version must be 1")

    packs = manifest.get("packs")
    if not isinstance(packs, list) or not packs:
        fail(failures, "packs must be a non-empty list")
        packs = []

    seen_ids: set[str] = set()
    seen_orders: set[int] = set()
    implemented_count = 0
    expansion_count = 0

    for pack in packs:
        pack_id, order = validate_pack(failures, pack)
        if pack_id is not None:
            if pack_id in seen_ids:
                fail(failures, f"{pack_id}: duplicate pack id")
            seen_ids.add(pack_id)
        if order is not None:
            if order in seen_orders:
                fail(failures, f"{pack_id}: duplicate pack order {order}")
            seen_orders.add(order)
        if isinstance(pack, dict):
            if pack.get("status") == "implemented":
                implemented_count += 1
            if pack.get("status") in {"configured_demo", "reserved", "planned"}:
                expansion_count += 1

    listed_orders = [pack.get("order") for pack in packs if isinstance(pack, dict)]
    if listed_orders != sorted(listed_orders):
        fail(failures, "packs must be listed in ascending order")

    if implemented_count < 1:
        fail(failures, "at least one implemented industry pack is required")
    if expansion_count < 1:
        fail(failures, "at least one reserved or planned expansion pack is required")

    if failures:
        print("Industry pack manifest check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Industry pack manifest check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
