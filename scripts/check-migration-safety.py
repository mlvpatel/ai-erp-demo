#!/usr/bin/env python3
"""Validate Frappe migration safety guardrails."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "migration-safety.json"


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
        fail(failures, "migration-safety.json schema_version must be 1")
    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        fail(failures, "description must be a non-empty string")

    for field in (
        "workflow_doc",
        "quality_gates_doc",
        "dependency_workflow_doc",
        "local_demo_runbook",
        "fresh_clone_demo",
        "dev_helper",
        "bootstrap_script",
    ):
        required_path(manifest, field, failures)

    for field in (
        "apps",
        "dev_helper_required_snippets",
        "demo_check_order",
        "bootstrap_required_snippets",
        "fresh_clone_required_step_ids",
        "required_doc_phrases",
        "forbidden_schema_sql",
        "scan_paths",
    ):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            fail(failures, f"{field} must be a non-empty list")


def validate_apps(manifest: dict[str, Any], failures: list[str]) -> None:
    for index, app in enumerate(manifest.get("apps", []), 1):
        if not isinstance(app, dict):
            fail(failures, f"apps[{index}] must be an object")
            continue
        app_name = app.get("name")
        if not isinstance(app_name, str) or not app_name:
            fail(failures, f"apps[{index}].name must be a non-empty string")
            app_name = f"apps[{index}]"

        hooks_path = app.get("hooks")
        patches_path = app.get("patches")
        if not isinstance(hooks_path, str) or not isinstance(patches_path, str):
            fail(failures, f"{app_name}: hooks and patches must be paths")
            continue

        hooks_text = read_text(REPO_ROOT / hooks_path, failures)
        for snippet in string_list(app.get("required_hook_snippets"), f"{app_name}.required_hook_snippets", failures):
            if not contains_snippet(hooks_text, snippet):
                fail(failures, f"{app_name}: hooks missing snippet: {snippet}")

        validate_empty_patches(app_name, REPO_ROOT / patches_path, failures)
        for doctype_path in string_list(app.get("doctypes"), f"{app_name}.doctypes", failures):
            value = load_json(REPO_ROOT / doctype_path, failures)
            if not isinstance(value, dict):
                continue
            if value.get("doctype") != "DocType":
                fail(failures, f"{doctype_path}: expected doctype marker 'DocType'")
            if not isinstance(value.get("name"), str) or not value["name"]:
                fail(failures, f"{doctype_path}: DocType JSON must have a name")


def validate_empty_patches(app_name: str, path: Path, failures: list[str]) -> None:
    text = read_text(path, failures)
    allowed_sections = {"[pre_model_sync]", "[post_model_sync]"}
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped in allowed_sections:
            continue
        fail(failures, f"{app_name}: patches.txt has active entry on line {line_number}: {stripped}")


def validate_dev_helper(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("dev_helper")
    if not isinstance(path_value, str):
        return
    text = read_text(REPO_ROOT / path_value, failures)
    for snippet in string_list(manifest.get("dev_helper_required_snippets"), "dev_helper_required_snippets", failures):
        if not contains_snippet(text, snippet):
            fail(failures, f"{path_value} missing migration snippet: {snippet}")

    position = -1
    for snippet in string_list(manifest.get("demo_check_order"), "demo_check_order", failures):
        next_position = text.find(snippet, position + 1)
        if next_position == -1:
            fail(failures, f"{path_value} missing demo-check ordered snippet: {snippet}")
            return
        position = next_position


def validate_bootstrap(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("bootstrap_script")
    if not isinstance(path_value, str):
        return
    text = read_text(REPO_ROOT / path_value, failures)
    for snippet in string_list(manifest.get("bootstrap_required_snippets"), "bootstrap_required_snippets", failures):
        if not contains_snippet(text, snippet):
            fail(failures, f"{path_value} missing bootstrap snippet: {snippet}")


def validate_fresh_clone_steps(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("fresh_clone_demo")
    if not isinstance(path_value, str):
        return
    value = load_json(REPO_ROOT / path_value, failures)
    if not isinstance(value, dict):
        return
    steps = value.get("steps")
    if not isinstance(steps, list):
        fail(failures, f"{path_value}: steps must be a list")
        return
    step_ids = {
        step.get("id")
        for step in steps
        if isinstance(step, dict) and isinstance(step.get("id"), str)
    }
    for step_id in string_list(
        manifest.get("fresh_clone_required_step_ids"),
        "fresh_clone_required_step_ids",
        failures,
    ):
        if step_id not in step_ids:
            fail(failures, f"{path_value}: missing migration/demo step id {step_id}")


def validate_docs(manifest: dict[str, Any], failures: list[str]) -> None:
    doc_text = "\n".join(
        read_text(REPO_ROOT / path_value, failures)
        for path_value in (
            manifest.get("workflow_doc"),
            manifest.get("quality_gates_doc"),
            manifest.get("dependency_workflow_doc"),
            manifest.get("local_demo_runbook"),
        )
        if isinstance(path_value, str)
    )
    for phrase in string_list(manifest.get("required_doc_phrases"), "required_doc_phrases", failures):
        if not contains_snippet(doc_text, phrase):
            fail(failures, f"migration safety docs missing phrase: {phrase}")


def iter_text_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.is_file():
        return [root]
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix.lower() in {".py", ".js", ".json", ".txt", ".md", ".yaml", ".yml", ".toml"}
    ]


def validate_no_direct_schema_ddl(manifest: dict[str, Any], failures: list[str]) -> None:
    terms = string_list(manifest.get("forbidden_schema_sql"), "forbidden_schema_sql", failures)
    for path_value in string_list(manifest.get("scan_paths"), "scan_paths", failures):
        root = REPO_ROOT / path_value
        if not root.exists():
            fail(failures, f"schema SQL scan path is missing: {path_value}")
            continue
        for file_path in iter_text_files(root):
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            upper_text = text.upper()
            for term in terms:
                if term.upper() in upper_text:
                    fail(failures, f"{rel(file_path)} contains forbidden schema DDL: {term}")


def main() -> int:
    failures: list[str] = []
    value = load_json(MANIFEST_PATH, failures)
    manifest = value if isinstance(value, dict) else {}

    if manifest:
        validate_shape(manifest, failures)
        validate_apps(manifest, failures)
        validate_dev_helper(manifest, failures)
        validate_bootstrap(manifest, failures)
        validate_fresh_clone_steps(manifest, failures)
        validate_docs(manifest, failures)
        validate_no_direct_schema_ddl(manifest, failures)

    if failures:
        print("Migration safety check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Migration safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
