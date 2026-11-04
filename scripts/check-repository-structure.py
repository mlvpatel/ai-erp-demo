#!/usr/bin/env python3
"""Validate the ERP-specific repository structure."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from _gate import REPO_ROOT, rel, report


MANIFEST = REPO_ROOT / "config" / "repository-structure.json"


def load_manifest(failures: list[str]) -> dict[str, Any]:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"missing structure manifest: {rel(MANIFEST)}")
        return {}
    except json.JSONDecodeError as exc:
        failures.append(f"invalid JSON in {rel(MANIFEST)}: {exc}")
        return {}

    return manifest


def require_string_list(
    failures: list[str], manifest: dict[str, Any], field: str
) -> list[str]:
    value = manifest.get(field)
    if not isinstance(value, list) or not value:
        failures.append(f"{field} must be a non-empty list")
        return []
    if any(not isinstance(item, str) or not item.strip() for item in value):
        failures.append(f"{field} must contain non-empty strings")
        return []
    return value


def validate_required_paths(failures: list[str], manifest: dict[str, Any]) -> None:
    for directory in require_string_list(failures, manifest, "required_directories"):
        path = REPO_ROOT / directory
        if not path.is_dir():
            failures.append(f"missing required directory: {directory}")

    for file_path in require_string_list(failures, manifest, "required_files"):
        path = REPO_ROOT / file_path
        if not path.is_file():
            failures.append(f"missing required file: {file_path}")


def validate_root_entries(failures: list[str], manifest: dict[str, Any]) -> None:
    required_directories = require_string_list(failures, manifest, "required_directories")
    required_files = require_string_list(failures, manifest, "required_files")
    allowed_entries = require_string_list(failures, manifest, "allowed_root_entries")
    bounded_roots = manifest.get("bounded_roots")
    bounded_root_names = set(bounded_roots) if isinstance(bounded_roots, dict) else set()

    if len(set(allowed_entries)) != len(allowed_entries):
        failures.append("allowed_root_entries must not contain duplicates")
    for entry in allowed_entries:
        if "/" in entry or "\\" in entry or entry in {".", ".."}:
            failures.append(f"allowed_root_entries must contain root names only: {entry}")

    allowed_names = set(allowed_entries) | bounded_root_names
    allowed_names.update(Path(path).parts[0] for path in required_directories)
    allowed_names.update(Path(path).parts[0] for path in required_files)

    for entry in sorted(REPO_ROOT.iterdir(), key=lambda path: path.name):
        if entry.name not in allowed_names and not (_is_git_ignored(entry) and not _is_git_tracked(entry)):
            failures.append(f"unexpected repository root entry: {entry.name}")


def validate_forbidden_root_dirs(failures: list[str], manifest: dict[str, Any]) -> None:
    for directory in require_string_list(failures, manifest, "forbidden_root_directories"):
        path = REPO_ROOT / directory
        if path.exists():
            failures.append(
                f"forbidden generic root directory exists: {directory}; use ERP/Frappe-specific boundaries",
            )


def validate_implemented_apps(failures: list[str], manifest: dict[str, Any]) -> None:
    apps = manifest.get("implemented_apps")
    if not isinstance(apps, list) or not apps:
        failures.append("implemented_apps must be a non-empty list")
        return

    for app in apps:
        if not isinstance(app, dict):
            failures.append("implemented_apps entries must be objects")
            continue
        app_path_value = app.get("path")
        markers = app.get("markers")
        if not isinstance(app_path_value, str) or not app_path_value.strip():
            failures.append("implemented app path must be a non-empty string")
            continue
        app_path = REPO_ROOT / app_path_value
        if not app_path.is_dir():
            failures.append(f"implemented app directory missing: {app_path_value}")
            continue
        if not isinstance(markers, list) or not markers:
            failures.append(f"{app_path_value}: markers must be a non-empty list")
            continue
        for marker in markers:
            if not isinstance(marker, str) or not marker.strip():
                failures.append(f"{app_path_value}: marker must be a non-empty string")
                continue
            if not (app_path / marker).exists():
                failures.append(f"{app_path_value}: missing implemented app marker {marker}")


def validate_bounded_roots(failures: list[str], manifest: dict[str, Any]) -> None:
    bounded_roots = manifest.get("bounded_roots")
    if not isinstance(bounded_roots, dict) or not bounded_roots:
        failures.append("bounded_roots must be a non-empty object")
        return
    for root, description in bounded_roots.items():
        if not isinstance(root, str) or not isinstance(description, str) or not description.strip():
            failures.append("bounded_roots keys and descriptions must be non-empty strings")
            continue
        if not (REPO_ROOT / root).is_dir():
            failures.append(f"bounded root directory missing: {root}")


def _is_git_ignored(entry: Path) -> bool:
    try:
        return (
            subprocess.run(
                ["git", "check-ignore", "--quiet", str(entry.relative_to(REPO_ROOT))],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
            ).returncode
            == 0
        )
    except OSError:
        return False


def _is_git_tracked(entry: Path) -> bool:
    try:
        return (
            subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(entry.relative_to(REPO_ROOT))],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
            ).returncode
            == 0
        )
    except OSError:
        return False


def validate_local_only_agent_paths(failures: list[str], manifest: dict[str, Any]) -> None:
    """Agent instructions and skills stay on developer machines: gitignored and never tracked."""
    for path_value in require_string_list(failures, manifest, "local_only_agent_paths"):
        entry = REPO_ROOT / path_value
        if _is_git_tracked(entry):
            failures.append(f"agent path must not be tracked: {path_value}")
        if not _is_git_ignored(entry):
            failures.append(f"agent path must be gitignored: {path_value}")


def main() -> int:
    failures: list[str] = []
    manifest = load_manifest(failures)

    if manifest:
        validate_required_paths(failures, manifest)
        validate_root_entries(failures, manifest)
        validate_forbidden_root_dirs(failures, manifest)
        validate_implemented_apps(failures, manifest)
        validate_bounded_roots(failures, manifest)
        validate_local_only_agent_paths(failures, manifest)

    return report("Repository structure check", failures)


if __name__ == "__main__":
    raise SystemExit(main())
