#!/usr/bin/env python3
"""Validate audit evidence invariants for AI-supported ERP workflows."""

from __future__ import annotations

from typing import Any

from _gate import (
    REPO_ROOT,
    contains_snippet,
    joined_doc_phrases,
    load_json,
    load_json_object,
    read_text,
    report,
    required_path,
    string_list,
)


MANIFEST_PATH = REPO_ROOT / "config" / "audit-evidence.json"
DOC_FIELDS = ("workflow_doc", "review_checklist", "threat_model", "service_workflow_doc")


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    for field in (
        "workflow_doc",
        "review_checklist",
        "threat_model",
        "service_workflow_doc",
        "service_work_order_tests",
    ):
        required_path(manifest, field, failures)


    for field in ("doctype_fields", "source_checks", "test_anchors", "required_doc_phrases"):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            failures.append(f"{field} must be a non-empty list")


def validate_doctype_fields(manifest: dict[str, Any], failures: list[str]) -> None:
    seen_ids: set[str] = set()
    for index, spec in enumerate(manifest.get("doctype_fields", []), 1):
        if not isinstance(spec, dict):
            failures.append(f"doctype_fields[{index}] must be an object")
            continue
        spec_id = spec.get("id")
        if not isinstance(spec_id, str) or not spec_id:
            failures.append(f"doctype_fields[{index}].id must be a non-empty string")
            spec_id = f"doctype_fields[{index}]"
        elif spec_id in seen_ids:
            failures.append(f"{spec_id}: duplicate doctype field spec id")
        seen_ids.add(spec_id)

        doctype = spec.get("doctype")
        path_value = spec.get("path")
        if not isinstance(doctype, str) or not doctype.strip():
            failures.append(f"{spec_id}: doctype must be a non-empty string")
        if not isinstance(path_value, str) or not path_value.strip():
            failures.append(f"{spec_id}: path must be a non-empty string")
            continue

        doctype_json = load_json_object(REPO_ROOT / path_value, failures)
        if not isinstance(doctype_json, dict):
            continue
        if isinstance(doctype, str) and doctype_json.get("name") != doctype:
            failures.append(f"{spec_id}: expected DocType name {doctype}")

        fields = doctype_json.get("fields")
        if not isinstance(fields, list):
            failures.append(f"{spec_id}: DocType fields must be a list")
            continue
        by_name = {
            field.get("fieldname"): field
            for field in fields
            if isinstance(field, dict) and isinstance(field.get("fieldname"), str)
        }

        required_fields = spec.get("required_fields")
        if not isinstance(required_fields, list) or not required_fields:
            failures.append(f"{spec_id}: required_fields must be a non-empty list")
            continue
        for field_index, expected in enumerate(required_fields, 1):
            if not isinstance(expected, dict):
                failures.append(f"{spec_id}.required_fields[{field_index}] must be an object")
                continue
            fieldname = expected.get("fieldname")
            if not isinstance(fieldname, str) or not fieldname:
                failures.append(f"{spec_id}.required_fields[{field_index}].fieldname must be non-empty")
                continue
            actual = by_name.get(fieldname)
            if actual is None:
                failures.append(f"{spec_id}: missing field {fieldname}")
                continue
            expected_type = expected.get("fieldtype")
            if isinstance(expected_type, str) and actual.get("fieldtype") != expected_type:
                failures.append(
                    f"{spec_id}.{fieldname}: expected fieldtype {expected_type}, got {actual.get('fieldtype')}",
                )
            if "options" in expected and actual.get("options", "") != expected["options"]:
                failures.append(
                    f"{spec_id}.{fieldname}: expected options {expected['options']!r}, got {actual.get('options', '')!r}",
                )


def validate_source_checks(manifest: dict[str, Any], failures: list[str]) -> None:
    seen_ids: set[str] = set()
    for index, check in enumerate(manifest.get("source_checks", []), 1):
        if not isinstance(check, dict):
            failures.append(f"source_checks[{index}] must be an object")
            continue
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            failures.append(f"source_checks[{index}].id must be a non-empty string")
            check_id = f"source_checks[{index}]"
        elif check_id in seen_ids:
            failures.append(f"{check_id}: duplicate source check id")
        seen_ids.add(check_id)

        path_value = check.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            failures.append(f"{check_id}: path must be a non-empty string")
            continue
        source_text = read_text(REPO_ROOT / path_value, failures)
        for snippet in string_list(check.get("required_snippets"), f"{check_id}.required_snippets", failures):
            if not contains_snippet(source_text, snippet):
                failures.append(f"{check_id}: {path_value} missing source snippet: {snippet}")


def validate_test_anchors(manifest: dict[str, Any], failures: list[str]) -> None:
    test_path = manifest.get("service_work_order_tests")
    test_text = read_text(REPO_ROOT / test_path, failures) if isinstance(test_path, str) else ""
    for anchor in string_list(manifest.get("test_anchors"), "test_anchors", failures):
        if not contains_snippet(test_text, anchor):
            failures.append(f"service workflow tests missing audit anchor: {anchor}")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_doctype_fields(manifest, failures)
        validate_source_checks(manifest, failures)
        validate_test_anchors(manifest, failures)
        joined_doc_phrases(manifest, DOC_FIELDS, "audit evidence", failures)

    return report("Audit evidence check", failures)


if __name__ == "__main__":
    raise SystemExit(main())
