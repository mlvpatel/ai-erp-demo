#!/usr/bin/env python3
"""Validate the ERP-specific repository structure."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "config" / "repository-structure.json"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def load_manifest(failures: list[str]) -> dict[str, Any]:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(failures, f"missing structure manifest: {rel(MANIFEST)}")
        return {}
    except json.JSONDecodeError as exc:
        fail(failures, f"invalid JSON in {rel(MANIFEST)}: {exc}")
        return {}

    if manifest.get("schema_version") != 1:
        fail(failures, "repository-structure schema_version must be 1")
    return manifest


def require_string_list(
    failures: list[str], manifest: dict[str, Any], field: str
) -> list[str]:
    value = manifest.get(field)
    if not isinstance(value, list) or not value:
        fail(failures, f"{field} must be a non-empty list")
        return []
    if any(not isinstance(item, str) or not item.strip() for item in value):
        fail(failures, f"{field} must contain non-empty strings")
        return []
    return value


def validate_required_paths(failures: list[str], manifest: dict[str, Any]) -> None:
    for directory in require_string_list(failures, manifest, "required_directories"):
        path = REPO_ROOT / directory
        if not path.is_dir():
            fail(failures, f"missing required directory: {directory}")

    for file_path in require_string_list(failures, manifest, "required_files"):
        path = REPO_ROOT / file_path
        if not path.is_file():
            fail(failures, f"missing required file: {file_path}")


def validate_forbidden_root_dirs(failures: list[str], manifest: dict[str, Any]) -> None:
    for directory in require_string_list(failures, manifest, "forbidden_root_directories"):
        path = REPO_ROOT / directory
        if path.exists():
            fail(
                failures,
                f"forbidden generic root directory exists: {directory}; use ERP/Frappe-specific boundaries",
            )


def validate_implemented_apps(failures: list[str], manifest: dict[str, Any]) -> None:
    apps = manifest.get("implemented_apps")
    if not isinstance(apps, list) or not apps:
        fail(failures, "implemented_apps must be a non-empty list")
        return

    for app in apps:
        if not isinstance(app, dict):
            fail(failures, "implemented_apps entries must be objects")
            continue
        app_path_value = app.get("path")
        markers = app.get("markers")
        if not isinstance(app_path_value, str) or not app_path_value.strip():
            fail(failures, "implemented app path must be a non-empty string")
            continue
        app_path = REPO_ROOT / app_path_value
        if not app_path.is_dir():
            fail(failures, f"implemented app directory missing: {app_path_value}")
            continue
        if not isinstance(markers, list) or not markers:
            fail(failures, f"{app_path_value}: markers must be a non-empty list")
            continue
        for marker in markers:
            if not isinstance(marker, str) or not marker.strip():
                fail(failures, f"{app_path_value}: marker must be a non-empty string")
                continue
            if not (app_path / marker).exists():
                fail(failures, f"{app_path_value}: missing implemented app marker {marker}")


def validate_reserved_apps(failures: list[str], manifest: dict[str, Any]) -> None:
    reserved_apps = require_string_list(failures, manifest, "reserved_doc_only_apps")
    forbidden_markers = require_string_list(failures, manifest, "reserved_app_forbidden_markers")

    for app_path_value in reserved_apps:
        app_path = REPO_ROOT / app_path_value
        if not app_path.is_dir():
            fail(failures, f"reserved app directory missing: {app_path_value}")
            continue
        if not (app_path / "README.md").is_file():
            fail(failures, f"reserved app must have README.md: {app_path_value}")
        for marker in forbidden_markers:
            if (app_path / marker).exists():
                fail(
                    failures,
                    f"reserved app contains generated marker before discovery gate: {app_path_value}/{marker}",
                )


def validate_bounded_roots(failures: list[str], manifest: dict[str, Any]) -> None:
    bounded_roots = manifest.get("bounded_roots")
    if not isinstance(bounded_roots, dict) or not bounded_roots:
        fail(failures, "bounded_roots must be a non-empty object")
        return
    for root, description in bounded_roots.items():
        if not isinstance(root, str) or not isinstance(description, str) or not description.strip():
            fail(failures, "bounded_roots keys and descriptions must be non-empty strings")
            continue
        if not (REPO_ROOT / root).is_dir():
            fail(failures, f"bounded root directory missing: {root}")


def main() -> int:
    failures: list[str] = []
    manifest = load_manifest(failures)

    if manifest:
        validate_required_paths(failures, manifest)
        validate_forbidden_root_dirs(failures, manifest)
        validate_implemented_apps(failures, manifest)
        validate_reserved_apps(failures, manifest)
        validate_bounded_roots(failures, manifest)

    if failures:
        print("Repository structure check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Repository structure check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
