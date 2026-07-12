#!/usr/bin/env python3
"""Validate audit evidence invariants for AI-supported ERP workflows."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "audit-evidence.json"


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
        fail(failures, "audit-evidence.json schema_version must be 1")

    for field in (
        "workflow_doc",
        "review_checklist",
        "threat_model",
        "service_workflow_doc",
        "service_work_order_tests",
    ):
        required_path(manifest, field, failures)

    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        fail(failures, "description must be a non-empty string")

    for field in ("doctype_fields", "source_checks", "test_anchors", "required_doc_phrases"):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            fail(failures, f"{field} must be a non-empty list")


def validate_doctype_fields(manifest: dict[str, Any], failures: list[str]) -> None:
    seen_ids: set[str] = set()
    for index, spec in enumerate(manifest.get("doctype_fields", []), 1):
        if not isinstance(spec, dict):
            fail(failures, f"doctype_fields[{index}] must be an object")
            continue
        spec_id = spec.get("id")
        if not isinstance(spec_id, str) or not spec_id:
            fail(failures, f"doctype_fields[{index}].id must be a non-empty string")
            spec_id = f"doctype_fields[{index}]"
        elif spec_id in seen_ids:
            fail(failures, f"{spec_id}: duplicate doctype field spec id")
        seen_ids.add(spec_id)

        doctype = spec.get("doctype")
        path_value = spec.get("path")
        if not isinstance(doctype, str) or not doctype.strip():
            fail(failures, f"{spec_id}: doctype must be a non-empty string")
        if not isinstance(path_value, str) or not path_value.strip():
            fail(failures, f"{spec_id}: path must be a non-empty string")
            continue

        doctype_json = load_json(REPO_ROOT / path_value, failures)
        if not isinstance(doctype_json, dict):
            continue
        if isinstance(doctype, str) and doctype_json.get("name") != doctype:
            fail(failures, f"{spec_id}: expected DocType name {doctype}")

        fields = doctype_json.get("fields")
        if not isinstance(fields, list):
            fail(failures, f"{spec_id}: DocType fields must be a list")
            continue
        by_name = {
            field.get("fieldname"): field
            for field in fields
            if isinstance(field, dict) and isinstance(field.get("fieldname"), str)
        }

        required_fields = spec.get("required_fields")
        if not isinstance(required_fields, list) or not required_fields:
            fail(failures, f"{spec_id}: required_fields must be a non-empty list")
            continue
        for field_index, expected in enumerate(required_fields, 1):
            if not isinstance(expected, dict):
                fail(failures, f"{spec_id}.required_fields[{field_index}] must be an object")
                continue
            fieldname = expected.get("fieldname")
            if not isinstance(fieldname, str) or not fieldname:
                fail(failures, f"{spec_id}.required_fields[{field_index}].fieldname must be non-empty")
                continue
            actual = by_name.get(fieldname)
            if actual is None:
                fail(failures, f"{spec_id}: missing field {fieldname}")
                continue
            expected_type = expected.get("fieldtype")
            if isinstance(expected_type, str) and actual.get("fieldtype") != expected_type:
                fail(
                    failures,
                    f"{spec_id}.{fieldname}: expected fieldtype {expected_type}, got {actual.get('fieldtype')}",
                )
            if "options" in expected and actual.get("options", "") != expected["options"]:
                fail(
                    failures,
                    f"{spec_id}.{fieldname}: expected options {expected['options']!r}, got {actual.get('options', '')!r}",
                )


def validate_source_checks(manifest: dict[str, Any], failures: list[str]) -> None:
    seen_ids: set[str] = set()
    for index, check in enumerate(manifest.get("source_checks", []), 1):
        if not isinstance(check, dict):
            fail(failures, f"source_checks[{index}] must be an object")
            continue
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            fail(failures, f"source_checks[{index}].id must be a non-empty string")
            check_id = f"source_checks[{index}]"
        elif check_id in seen_ids:
            fail(failures, f"{check_id}: duplicate source check id")
        seen_ids.add(check_id)

        path_value = check.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            fail(failures, f"{check_id}: path must be a non-empty string")
            continue
        source_text = read_text(REPO_ROOT / path_value, failures)
        for snippet in string_list(check.get("required_snippets"), f"{check_id}.required_snippets", failures):
            if not contains_snippet(source_text, snippet):
                fail(failures, f"{check_id}: {path_value} missing source snippet: {snippet}")


def validate_test_anchors(manifest: dict[str, Any], failures: list[str]) -> None:
    test_path = manifest.get("service_work_order_tests")
    test_text = read_text(REPO_ROOT / test_path, failures) if isinstance(test_path, str) else ""
    for anchor in string_list(manifest.get("test_anchors"), "test_anchors", failures):
        if not contains_snippet(test_text, anchor):
            fail(failures, f"service workflow tests missing audit anchor: {anchor}")


def validate_docs(manifest: dict[str, Any], failures: list[str]) -> None:
    doc_text = "\n".join(
        read_text(REPO_ROOT / path_value, failures)
        for path_value in (
            manifest.get("workflow_doc"),
            manifest.get("review_checklist"),
            manifest.get("threat_model"),
            manifest.get("service_workflow_doc"),
        )
        if isinstance(path_value, str)
    )
    for phrase in string_list(manifest.get("required_doc_phrases"), "required_doc_phrases", failures):
        if not contains_snippet(doc_text, phrase):
            fail(failures, f"audit evidence docs missing phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    value = load_json(MANIFEST_PATH, failures)
    manifest = value if isinstance(value, dict) else {}

    if manifest:
        validate_shape(manifest, failures)
        validate_doctype_fields(manifest, failures)
        validate_source_checks(manifest, failures)
        validate_test_anchors(manifest, failures)
        validate_docs(manifest, failures)

    if failures:
        print("Audit evidence check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Audit evidence check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
