#!/usr/bin/env python3
"""Validate ERP authorization and approval guardrail evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / "config" / "authorization-matrix.json"


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


def validate_shape(matrix: dict[str, Any], failures: list[str]) -> None:
    if matrix.get("schema_version") != 1:
        fail(failures, "authorization-matrix.json schema_version must be 1")

    for field in ("workflow_doc", "service_workflow_doc", "threat_model", "test_file"):
        value = matrix.get(field)
        if not isinstance(value, str) or not value.strip():
            fail(failures, f"{field} must be a non-empty string")
        elif not (REPO_ROOT / value).is_file():
            fail(failures, f"{field} path is missing: {value}")

    for field in ("role_fixtures", "required_roles", "doctype_permissions", "sensitive_actions", "required_doc_phrases"):
        value = matrix.get(field)
        if not isinstance(value, list) or not value:
            fail(failures, f"{field} must be a non-empty list")


def collect_fixture_roles(matrix: dict[str, Any], failures: list[str]) -> set[str]:
    roles: set[str] = set()
    for fixture_path in string_list(matrix.get("role_fixtures"), "role_fixtures", failures):
        value = load_json(REPO_ROOT / fixture_path, failures)
        if not isinstance(value, list):
            fail(failures, f"{fixture_path}: role fixture must contain a list")
            continue
        for item in value:
            if not isinstance(item, dict):
                fail(failures, f"{fixture_path}: every role fixture entry must be an object")
                continue
            role = item.get("role_name") or item.get("name")
            if isinstance(role, str) and role.strip():
                roles.add(role)
    return roles


def validate_roles(matrix: dict[str, Any], failures: list[str]) -> None:
    roles = collect_fixture_roles(matrix, failures)
    for role in string_list(matrix.get("required_roles"), "required_roles", failures):
        if role not in roles:
            fail(failures, f"required role is missing from fixtures: {role}")


def permission_enabled(permission: dict[str, Any], right: str) -> bool:
    value = permission.get(right)
    return value == 1 or value is True


def validate_doctype_permissions(matrix: dict[str, Any], failures: list[str]) -> None:
    hooks_cache: dict[str, str] = {}
    for index, entry in enumerate(matrix.get("doctype_permissions", []), 1):
        if not isinstance(entry, dict):
            fail(failures, f"doctype_permissions[{index}] must be an object")
            continue
        doctype = entry.get("doctype")
        path_value = entry.get("path")
        if not isinstance(doctype, str) or not isinstance(path_value, str):
            fail(failures, f"doctype_permissions[{index}] must set doctype and path")
            continue
        doctype_json = load_json(REPO_ROOT / path_value, failures)
        if not isinstance(doctype_json, dict):
            continue
        if doctype_json.get("name") != doctype:
            fail(failures, f"{path_value}: expected DocType name {doctype}")
        permissions = doctype_json.get("permissions")
        if not isinstance(permissions, list):
            fail(failures, f"{path_value}: permissions must be a list")
            continue
        by_role = {
            permission.get("role"): permission
            for permission in permissions
            if isinstance(permission, dict) and isinstance(permission.get("role"), str)
        }
        required_roles = entry.get("required_roles")
        if not isinstance(required_roles, dict):
            fail(failures, f"{doctype}: required_roles must be an object")
            continue
        for role, rights in required_roles.items():
            if role not in by_role:
                fail(failures, f"{doctype}: missing DocType permission row for {role}")
                continue
            if not isinstance(rights, list) or not rights:
                fail(failures, f"{doctype}: required rights for {role} must be a non-empty list")
                continue
            for right in rights:
                if not isinstance(right, str) or not permission_enabled(by_role[role], right):
                    fail(failures, f"{doctype}: role {role} must have {right} permission")

        hook = entry.get("permission_query_hook")
        has_permission = entry.get("has_permission_hook")
        for hook_value in (hook, has_permission):
            if not isinstance(hook_value, str) or "." not in hook_value:
                fail(failures, f"{doctype}: hook values must be dotted Python paths")
                continue
            app_module = hook_value.split(".", 1)[0]
            hooks_path = REPO_ROOT / "apps" / app_module / app_module / "hooks.py"
            hook_text = hooks_cache.setdefault(str(hooks_path), read_text(hooks_path, failures))
            if hook_value not in hook_text or doctype not in hook_text:
                fail(failures, f"{doctype}: hooks.py must register {hook_value}")


def validate_sensitive_actions(matrix: dict[str, Any], failures: list[str]) -> None:
    test_file = matrix.get("test_file")
    test_text = read_text(REPO_ROOT / test_file, failures) if isinstance(test_file, str) else ""
    seen_ids: set[str] = set()

    for index, action in enumerate(matrix.get("sensitive_actions", []), 1):
        if not isinstance(action, dict):
            fail(failures, f"sensitive_actions[{index}] must be an object")
            continue
        action_id = action.get("id")
        if not isinstance(action_id, str) or not action_id:
            fail(failures, f"sensitive_actions[{index}].id must be non-empty")
            action_id = f"sensitive_actions[{index}]"
        elif action_id in seen_ids:
            fail(failures, f"{action_id}: duplicate sensitive action id")
        seen_ids.add(action_id)

        string_list(action.get("roles_allowed"), f"{action_id}.roles_allowed", failures)
        guard_files = action.get("guard_files")
        if not isinstance(guard_files, list) or not guard_files:
            fail(failures, f"{action_id}: guard_files must be a non-empty list")
        else:
            for guard_index, guard in enumerate(guard_files, 1):
                if not isinstance(guard, dict):
                    fail(failures, f"{action_id}.guard_files[{guard_index}] must be an object")
                    continue
                path_value = guard.get("path")
                if not isinstance(path_value, str):
                    fail(failures, f"{action_id}.guard_files[{guard_index}].path must be a string")
                    continue
                source = read_text(REPO_ROOT / path_value, failures)
                for snippet in string_list(
                    guard.get("required_snippets"),
                    f"{action_id}.guard_files[{guard_index}].required_snippets",
                    failures,
                ):
                    if not contains_snippet(source, snippet):
                        fail(failures, f"{action_id}: {path_value} missing guard snippet: {snippet}")

        for anchor in string_list(action.get("test_anchors"), f"{action_id}.test_anchors", failures):
            if not contains_snippet(test_text, anchor):
                fail(failures, f"{action_id}: test file missing anchor: {anchor}")


def validate_docs(matrix: dict[str, Any], failures: list[str]) -> None:
    doc_text = "\n".join(
        read_text(REPO_ROOT / path_value, failures)
        for path_value in (
            matrix.get("workflow_doc"),
            matrix.get("service_workflow_doc"),
            matrix.get("threat_model"),
        )
        if isinstance(path_value, str)
    )
    for phrase in string_list(matrix.get("required_doc_phrases"), "required_doc_phrases", failures):
        if not contains_snippet(doc_text, phrase):
            fail(failures, f"authorization docs missing phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    value = load_json(MATRIX_PATH, failures)
    matrix = value if isinstance(value, dict) else {}

    if matrix:
        validate_shape(matrix, failures)
        validate_roles(matrix, failures)
        validate_doctype_permissions(matrix, failures)
        validate_sensitive_actions(matrix, failures)
        validate_docs(matrix, failures)

    if failures:
        print("Authorization matrix check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Authorization matrix check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
