#!/usr/bin/env python3
"""Validate upstream Frappe/ERPNext upgrade readiness guardrails."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "upstream-upgrade-readiness.json"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def load_json(path: Path, failures: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(failures, f"missing JSON file: {rel(path)}")
    except json.JSONDecodeError as exc:
        fail(failures, f"invalid JSON in {rel(path)}: {exc}")
    return None


def read_text(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(failures, f"missing file: {rel(path)}")
        return ""
    except UnicodeDecodeError as exc:
        fail(failures, f"expected UTF-8 text file: {rel(path)}: {exc}")
        return ""


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def contains_snippet(haystack: str, needle: str) -> bool:
    return normalize_space(needle) in normalize_space(haystack)


def string_list(value: Any, field: str, failures: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        fail(failures, f"{field} must be a non-empty list")
        return []
    result: list[str] = []
    for index, item in enumerate(value, 1):
        if not isinstance(item, str) or not item.strip():
            fail(failures, f"{field}[{index}] must be a non-empty string")
            continue
        result.append(item)
    return result


def required_path(manifest: dict[str, Any], field: str, failures: list[str]) -> str | None:
    value = manifest.get(field)
    if not isinstance(value, str) or not value.strip():
        fail(failures, f"{field} must be a non-empty string")
        return None
    if not (REPO_ROOT / value).is_file():
        fail(failures, f"{field} path is missing: {value}")
    return value


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    if manifest.get("schema_version") != 1:
        fail(failures, "upstream-upgrade-readiness.json schema_version must be 1")
    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        fail(failures, "description must be a non-empty string")

    for field in (
        "workflow_doc",
        "dependency_workflow_doc",
        "migration_safety_doc",
        "quality_gates_doc",
        "development_readme",
        "env_example",
        "bootstrap_script",
        "reproducibility_script",
        "github_publication_runbook",
        "traceability_doc",
    ):
        required_path(manifest, field, failures)

    for field in (
        "required_env_pins",
        "required_validation_commands",
        "bootstrap_required_snippets",
        "required_doc_phrases",
    ):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            fail(failures, f"{field} must be a non-empty list")


def validate_env_pins(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("env_example")
    if not isinstance(path_value, str):
        return
    env_text = read_text(REPO_ROOT / path_value, failures)
    for pin in string_list(manifest.get("required_env_pins"), "required_env_pins", failures):
        if not re.search(rf"^{re.escape(pin)}=", env_text, flags=re.MULTILINE):
            fail(failures, f"{path_value} missing pin: {pin}")

    if not re.search(r"^FRAPPE_BRANCH=version-[0-9]+$", env_text, flags=re.MULTILINE):
        fail(failures, f"{path_value} must pin FRAPPE_BRANCH to an explicit version branch")
    for commit_pin in ("FRAPPE_COMMIT", "ERPNEXT_COMMIT"):
        if not re.search(rf"^{commit_pin}=[0-9a-f]{{40}}$", env_text, flags=re.MULTILINE):
            fail(failures, f"{path_value} {commit_pin} must be a full 40-character commit hash")
    for image_pin in ("MARIADB_IMAGE", "REDIS_IMAGE", "FRAPPE_BENCH_IMAGE"):
        if not re.search(rf"^{image_pin}=\S+@sha256:[0-9a-f]{{64}}$", env_text, flags=re.MULTILINE):
            fail(failures, f"{path_value} {image_pin} must be digest-pinned")


def validate_bootstrap(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("bootstrap_script")
    if not isinstance(path_value, str):
        return
    text = read_text(REPO_ROOT / path_value, failures)
    for snippet in string_list(manifest.get("bootstrap_required_snippets"), "bootstrap_required_snippets", failures):
        if not contains_snippet(text, snippet):
            fail(failures, f"{path_value} missing bootstrap safety snippet: {snippet}")


def validate_workflow_commands(manifest: dict[str, Any], failures: list[str]) -> None:
    workflow_path = manifest.get("workflow_doc")
    if not isinstance(workflow_path, str):
        return
    text = read_text(REPO_ROOT / workflow_path, failures)
    for command in string_list(manifest.get("required_validation_commands"), "required_validation_commands", failures):
        if not contains_snippet(text, command):
            fail(failures, f"{workflow_path} missing validation command: {command}")


def validate_docs(manifest: dict[str, Any], failures: list[str]) -> None:
    entries = manifest.get("required_doc_phrases")
    if not isinstance(entries, list):
        return
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            fail(failures, f"required_doc_phrases[{index}] must be an object")
            continue
        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value:
            fail(failures, f"required_doc_phrases[{index}].path must be a non-empty string")
            continue
        text = read_text(REPO_ROOT / path_value, failures)
        for phrase in string_list(entry.get("phrases"), f"required_doc_phrases[{index}].phrases", failures):
            if not contains_snippet(text, phrase):
                fail(failures, f"{path_value} missing upstream-upgrade phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    value = load_json(MANIFEST_PATH, failures)
    manifest = value if isinstance(value, dict) else {}

    if manifest:
        validate_shape(manifest, failures)
        validate_env_pins(manifest, failures)
        validate_bootstrap(manifest, failures)
        validate_workflow_commands(manifest, failures)
        validate_docs(manifest, failures)

    if failures:
        print("Upstream upgrade readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Upstream upgrade readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
