#!/usr/bin/env python3
"""Validate the ERP-specific repository structure."""

from __future__ import annotations

import json
import subprocess
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


def validate_root_entries(failures: list[str], manifest: dict[str, Any]) -> None:
    required_directories = require_string_list(failures, manifest, "required_directories")
    required_files = require_string_list(failures, manifest, "required_files")
    allowed_entries = require_string_list(failures, manifest, "allowed_root_entries")
    bounded_roots = manifest.get("bounded_roots")
    bounded_root_names = set(bounded_roots) if isinstance(bounded_roots, dict) else set()

    if len(set(allowed_entries)) != len(allowed_entries):
        fail(failures, "allowed_root_entries must not contain duplicates")
    for entry in allowed_entries:
        if "/" in entry or "\\" in entry or entry in {".", ".."}:
            fail(failures, f"allowed_root_entries must contain root names only: {entry}")

    allowed_names = set(allowed_entries) | bounded_root_names
    allowed_names.update(Path(path).parts[0] for path in required_directories)
    allowed_names.update(Path(path).parts[0] for path in required_files)

    for entry in sorted(REPO_ROOT.iterdir(), key=lambda path: path.name):
        if entry.name not in allowed_names and not _is_ignored_untracked(entry):
            fail(failures, f"unexpected repository root entry: {entry.name}")


def _is_ignored_untracked(entry: Path) -> bool:
    """Local working files excluded from version control are not layout drift."""
    try:
        ignored = (
            subprocess.run(
                ["git", "check-ignore", "--quiet", entry.name],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
            ).returncode
            == 0
        )
        tracked = (
            subprocess.run(
                ["git", "ls-files", "--error-unmatch", entry.name],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
            ).returncode
            == 0
        )
    except OSError:
        return False
    return ignored and not tracked


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


def validate_required_agent_skill_files(failures: list[str], manifest: dict[str, Any]) -> None:
    """Require tracked BEhuMan / agent skill files so prose and Cursor gates stay enforceable."""
    for path_value in require_string_list(failures, manifest, "required_agent_skill_files"):
        path = REPO_ROOT / path_value
        if not path.is_file():
            fail(failures, f"missing required agent skill file: {path_value}")
            continue
        if path.stat().st_size < 200:
            fail(failures, f"required agent skill file is empty or too small: {path_value}")
        if not _is_git_tracked(path):
            fail(failures, f"required agent skill file must be tracked by git: {path_value}")


def _validate_skill_tree(failures: list[str], skills_dir: Path, root_label: str, forbidden_lower: set[str]) -> None:
    if not skills_dir.is_dir():
        fail(failures, f"missing required directory: {root_label}/skills")
        return

    skill_dirs = sorted(
        (path for path in skills_dir.iterdir() if path.is_dir()),
        key=lambda path: path.name,
    )
    if not skill_dirs:
        fail(failures, f"{root_label}/skills must contain at least one skill directory")
    for skill_dir in skill_dirs:
        if not skill_dir.name.replace("-", "").isalnum() or skill_dir.name != skill_dir.name.lower():
            fail(failures, f"{root_label}/skills names must be lowercase kebab-case: {rel(skill_dir)}")
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            fail(failures, f"missing skill entrypoint: {rel(skill_md)}")
        for path in skill_dir.rglob("*"):
            if path.is_dir():
                continue
            relative = rel(path)
            if path.name.lower() in forbidden_lower:
                fail(failures, f"{root_label} forbids sensitive file: {relative}")
            if path.suffix.lower() in {".env", ".pem", ".key", ".p12", ".pfx"}:
                fail(failures, f"{root_label} forbids credential-like file: {relative}")
            if ".." in path.parts:
                fail(failures, f"{root_label} path traversal is forbidden: {relative}")


def validate_cursor_layout(failures: list[str], manifest: dict[str, Any]) -> None:
    """Hard-bound .cursor: skills and rules only; no secrets, MCP configs, or junk."""
    cursor_root = REPO_ROOT / ".cursor"
    if not cursor_root.is_dir():
        fail(failures, "bounded root directory missing: .cursor")
        return

    allowed_children = require_string_list(failures, manifest, "cursor_allowed_children")
    forbidden_names = require_string_list(failures, manifest, "cursor_forbidden_names")
    forbidden_lower = {name.lower() for name in forbidden_names}

    for child in sorted(cursor_root.iterdir(), key=lambda path: path.name):
        if child.name in allowed_children:
            continue
        if _is_git_ignored(child) and not _is_git_tracked(child):
            # Local-only ignored files may exist; they must never be tracked.
            continue
        if child.name.startswith(".") and child.name not in {".", ".."}:
            fail(failures, f".cursor forbids hidden entries: {rel(child)}")
            continue
        if child.name.lower() in forbidden_lower:
            fail(failures, f".cursor forbids sensitive or unmanaged path: {rel(child)}")
            continue
        fail(
            failures,
            f".cursor contains unexpected entry {child.name!r}; "
            f"allowed children: {', '.join(sorted(allowed_children))}",
        )

    rules_dir = cursor_root / "rules"
    if not rules_dir.is_dir():
        fail(failures, "missing required directory: .cursor/rules")
    else:
        rule_files = sorted(rules_dir.iterdir(), key=lambda path: path.name)
        if not rule_files:
            fail(failures, ".cursor/rules must contain at least one .mdc rule")
        for path in rule_files:
            if not path.is_file() or path.suffix != ".mdc":
                fail(failures, f".cursor/rules must contain only .mdc files: {rel(path)}")
                continue
            text = path.read_text(encoding="utf-8")
            if path.name == "behuman.mdc" and "alwaysApply: true" not in text:
                fail(failures, ".cursor/rules/behuman.mdc must set alwaysApply: true")
            if "behuman" in path.name and "SKILL.md" not in text:
                fail(failures, f"{rel(path)} must reference the behuman SKILL.md path")

    _validate_skill_tree(failures, cursor_root / "skills", ".cursor", forbidden_lower)


def validate_claude_layout(failures: list[str], manifest: dict[str, Any]) -> None:
    """Hard-bound .claude: mirrored skills only; local settings must stay untracked."""
    claude_root = REPO_ROOT / ".claude"
    if not claude_root.is_dir():
        fail(failures, "bounded root directory missing: .claude")
        return

    allowed_children = require_string_list(failures, manifest, "claude_allowed_children")
    forbidden_names = require_string_list(failures, manifest, "cursor_forbidden_names")
    forbidden_lower = {name.lower() for name in forbidden_names}

    for child in sorted(claude_root.iterdir(), key=lambda path: path.name):
        if child.name in allowed_children:
            continue
        if _is_git_tracked(child):
            fail(failures, f".claude must not track local/unmanaged path: {rel(child)}")
            continue
        if _is_git_ignored(child):
            continue
        if child.name.lower() in forbidden_lower:
            fail(failures, f".claude forbids sensitive or unmanaged path: {rel(child)}")
            continue
        fail(
            failures,
            f".claude contains unexpected entry {child.name!r}; "
            f"allowed children: {', '.join(sorted(allowed_children))}",
        )

    _validate_skill_tree(failures, claude_root / "skills", ".claude", forbidden_lower)


def validate_agents_layout(failures: list[str], manifest: dict[str, Any]) -> None:
    """Require shared .agents skills and forbid credential-like files there."""
    agents_root = REPO_ROOT / ".agents"
    if not agents_root.is_dir():
        fail(failures, "bounded root directory missing: .agents")
        return
    if not (agents_root / "AGENTS.md").is_file():
        fail(failures, "missing required file: .agents/AGENTS.md")
    skills_dir = agents_root / "skills"
    forbidden_lower = {
        name.lower() for name in require_string_list(failures, manifest, "cursor_forbidden_names")
    }
    _validate_skill_tree(failures, skills_dir, ".agents", forbidden_lower)


def main() -> int:
    failures: list[str] = []
    manifest = load_manifest(failures)

    if manifest:
        validate_required_paths(failures, manifest)
        validate_root_entries(failures, manifest)
        validate_forbidden_root_dirs(failures, manifest)
        validate_implemented_apps(failures, manifest)
        validate_reserved_apps(failures, manifest)
        validate_bounded_roots(failures, manifest)
        validate_required_agent_skill_files(failures, manifest)
        validate_agents_layout(failures, manifest)
        validate_claude_layout(failures, manifest)
        validate_cursor_layout(failures, manifest)

    if failures:
        print("Repository structure check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Repository structure check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
