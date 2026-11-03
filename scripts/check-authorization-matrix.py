#!/usr/bin/env python3
"""Validate ERP authorization and approval guardrail evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from _gate import REPO_ROOT, contains_snippet, read_text, rel, string_list


MATRIX_PATH = REPO_ROOT / "config" / "authorization-matrix.json"


# Role fixtures are JSON lists, so this gate keeps a loader that returns any JSON value.
def load_json_value(path: Path, failures: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"missing JSON file: {rel(path)}")
    except json.JSONDecodeError as exc:
        failures.append(f"invalid JSON in {rel(path)}: {exc}")
    return None


def validate_shape(matrix: dict[str, Any], failures: list[str]) -> None:
    for field in ("workflow_doc", "service_workflow_doc", "threat_model", "test_file"):
        value = matrix.get(field)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{field} must be a non-empty string")
        elif not (REPO_ROOT / value).is_file():
            failures.append(f"{field} path is missing: {value}")

    for field in ("role_fixtures", "required_roles", "doctype_permissions", "sensitive_actions", "required_doc_phrases"):
        value = matrix.get(field)
        if not isinstance(value, list) or not value:
            failures.append(f"{field} must be a non-empty list")


def collect_fixture_roles(matrix: dict[str, Any], failures: list[str]) -> set[str]:
    roles: set[str] = set()
    for fixture_path in string_list(matrix.get("role_fixtures"), "role_fixtures", failures):
        value = load_json_value(REPO_ROOT / fixture_path, failures)
        if not isinstance(value, list):
            failures.append(f"{fixture_path}: role fixture must contain a list")
            continue
        for item in value:
            if not isinstance(item, dict):
                failures.append(f"{fixture_path}: every role fixture entry must be an object")
                continue
            role = item.get("role_name") or item.get("name")
            if isinstance(role, str) and role.strip():
                roles.add(role)
    return roles


def validate_roles(matrix: dict[str, Any], failures: list[str]) -> None:
    roles = collect_fixture_roles(matrix, failures)
    for role in string_list(matrix.get("required_roles"), "required_roles", failures):
        if role not in roles:
            failures.append(f"required role is missing from fixtures: {role}")


def permission_enabled(permission: dict[str, Any], right: str) -> bool:
    value = permission.get(right)
    return value == 1 or value is True


def validate_doctype_permissions(matrix: dict[str, Any], failures: list[str]) -> None:
    hooks_cache: dict[str, str] = {}
    accounted_doctypes: set[str] = set()
    for index, entry in enumerate(matrix.get("doctype_permissions", []), 1):
        if not isinstance(entry, dict):
            failures.append(f"doctype_permissions[{index}] must be an object")
            continue
        doctype = entry.get("doctype")
        path_value = entry.get("path")
        if not isinstance(doctype, str) or not isinstance(path_value, str):
            failures.append(f"doctype_permissions[{index}] must set doctype and path")
            continue
        if doctype in accounted_doctypes:
            failures.append(f"duplicate doctype_permissions entry: {doctype}")
        accounted_doctypes.add(doctype)
        doctype_json = load_json_value(REPO_ROOT / path_value, failures)
        if not isinstance(doctype_json, dict):
            continue
        if doctype_json.get("name") != doctype:
            failures.append(f"{path_value}: expected DocType name {doctype}")
        permissions = doctype_json.get("permissions")
        if not isinstance(permissions, list):
            failures.append(f"{path_value}: permissions must be a list")
            continue
        by_role: dict[str, list[dict[str, Any]]] = {}
        for permission in permissions:
            if not isinstance(permission, dict) or not isinstance(permission.get("role"), str):
                continue
            by_role.setdefault(permission["role"], []).append(permission)
        required_roles = entry.get("required_roles")
        if not isinstance(required_roles, dict):
            failures.append(f"{doctype}: required_roles must be an object")
            continue
        for role, rights in required_roles.items():
            if role not in by_role:
                failures.append(f"{doctype}: missing DocType permission row for {role}")
                continue
            if not isinstance(rights, list) or not rights:
                failures.append(f"{doctype}: required rights for {role} must be a non-empty list")
                continue
            base_permissions = [row for row in by_role[role] if row.get("permlevel", 0) == 0]
            for right in rights:
                if not isinstance(right, str) or not any(
                    permission_enabled(permission, right) for permission in base_permissions
                ):
                    failures.append(f"{doctype}: role {role} must have {right} permission")

        record_scope = entry.get("record_scope", "hooked")
        hook = entry.get("permission_query_hook")
        has_permission = entry.get("has_permission_hook")
        if record_scope == "doctype_only":
            if hook is not None or has_permission is not None:
                failures.append(f"{doctype}: doctype_only scope must not declare row-level hooks")
            continue
        if record_scope != "hooked":
            failures.append(f"{doctype}: record_scope must be hooked or doctype_only")
            continue
        for hook_value in (hook, has_permission):
            if not isinstance(hook_value, str) or "." not in hook_value:
                failures.append(f"{doctype}: hook values must be dotted Python paths")
                continue
            app_module = hook_value.split(".", 1)[0]
            hooks_path = REPO_ROOT / "apps" / app_module / app_module / "hooks.py"
            hook_text = hooks_cache.setdefault(str(hooks_path), read_text(hooks_path, failures))
            if hook_value not in hook_text or doctype not in hook_text:
                failures.append(f"{doctype}: hooks.py must register {hook_value}")

    shipped_role_doctypes: set[str] = set()
    pattern = "apps/*/*/*/doctype/*/*.json"
    for doctype_path in REPO_ROOT.glob(pattern):
        doctype_json = load_json_value(doctype_path, failures)
        if not isinstance(doctype_json, dict):
            continue
        permissions = doctype_json.get("permissions")
        if not isinstance(permissions, list):
            continue
        if not any(isinstance(row, dict) and isinstance(row.get("role"), str) for row in permissions):
            continue
        doctype = doctype_json.get("name")
        if isinstance(doctype, str) and doctype:
            shipped_role_doctypes.add(doctype)

    for doctype in sorted(shipped_role_doctypes - accounted_doctypes):
        failures.append(f"role-bearing shipped DocType is missing from the matrix: {doctype}")
    for doctype in sorted(accounted_doctypes - shipped_role_doctypes):
        failures.append(f"matrix DocType is not a shipped role-bearing DocType: {doctype}")


def validate_sensitive_actions(matrix: dict[str, Any], failures: list[str]) -> None:
    test_file = matrix.get("test_file")
    test_text = read_text(REPO_ROOT / test_file, failures) if isinstance(test_file, str) else ""
    seen_ids: set[str] = set()

    for index, action in enumerate(matrix.get("sensitive_actions", []), 1):
        if not isinstance(action, dict):
            failures.append(f"sensitive_actions[{index}] must be an object")
            continue
        action_id = action.get("id")
        if not isinstance(action_id, str) or not action_id:
            failures.append(f"sensitive_actions[{index}].id must be non-empty")
            action_id = f"sensitive_actions[{index}]"
        elif action_id in seen_ids:
            failures.append(f"{action_id}: duplicate sensitive action id")
        seen_ids.add(action_id)

        string_list(action.get("roles_allowed"), f"{action_id}.roles_allowed", failures)
        guard_files = action.get("guard_files")
        if not isinstance(guard_files, list) or not guard_files:
            failures.append(f"{action_id}: guard_files must be a non-empty list")
        else:
            for guard_index, guard in enumerate(guard_files, 1):
                if not isinstance(guard, dict):
                    failures.append(f"{action_id}.guard_files[{guard_index}] must be an object")
                    continue
                path_value = guard.get("path")
                if not isinstance(path_value, str):
                    failures.append(f"{action_id}.guard_files[{guard_index}].path must be a string")
                    continue
                source = read_text(REPO_ROOT / path_value, failures)
                for snippet in string_list(
                    guard.get("required_snippets"),
                    f"{action_id}.guard_files[{guard_index}].required_snippets",
                    failures,
                ):
                    if not contains_snippet(source, snippet):
                        failures.append(f"{action_id}: {path_value} missing guard snippet: {snippet}")

        for anchor in string_list(action.get("test_anchors"), f"{action_id}.test_anchors", failures):
            if not contains_snippet(test_text, anchor):
                failures.append(f"{action_id}: test file missing anchor: {anchor}")


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
            failures.append(f"authorization docs missing phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    value = load_json_value(MATRIX_PATH, failures)
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
