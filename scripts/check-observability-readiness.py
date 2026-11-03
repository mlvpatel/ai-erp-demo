#!/usr/bin/env python3
"""Validate observability and alerting readiness guardrails."""

from __future__ import annotations

import sys
from typing import Any

from _gate import REPO_ROOT, load_json, read_text


MANIFEST_PATH = REPO_ROOT / "config" / "observability-readiness.json"


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def contains_snippet(haystack: str, needle: str) -> bool:
    return normalize_space(needle) in normalize_space(haystack)


def string_list(value: Any, field: str, failures: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        failures.append(f"{field} must be a non-empty list")
        return []
    result: list[str] = []
    for index, item in enumerate(value, 1):
        if not isinstance(item, str) or not item.strip():
            failures.append(f"{field}[{index}] must be a non-empty string")
            continue
        result.append(item)
    return result


def required_path(manifest: dict[str, Any], field: str, failures: list[str]) -> str | None:
    value = manifest.get(field)
    if not isinstance(value, str) or not value.strip():
        failures.append(f"{field} must be a non-empty string")
        return None
    if not (REPO_ROOT / value).is_file():
        failures.append(f"{field} path is missing: {value}")
    return value


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    required_path(manifest, "workflow_doc", failures)

    for field in (
        "signal_groups",
        "required_doc_phrases",
    ):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            failures.append(f"{field} must be a non-empty list")


def validate_signal_groups(manifest: dict[str, Any], failures: list[str]) -> None:
    workflow_path = manifest.get("workflow_doc")
    if not isinstance(workflow_path, str):
        return
    workflow_text = read_text(REPO_ROOT / workflow_path, failures)
    groups = manifest.get("signal_groups")
    if not isinstance(groups, list):
        return
    seen: set[str] = set()
    for index, group in enumerate(groups, 1):
        if not isinstance(group, dict):
            failures.append(f"signal_groups[{index}] must be an object")
            continue
        group_id = group.get("id")
        if not isinstance(group_id, str) or not group_id.strip():
            failures.append(f"signal_groups[{index}].id must be a non-empty string")
        elif group_id in seen:
            failures.append(f"duplicate signal group id: {group_id}")
        else:
            seen.add(group_id)
        for term in string_list(group.get("required_terms"), f"signal_groups[{index}].required_terms", failures):
            if not contains_snippet(workflow_text, term):
                failures.append(f"{workflow_path} missing signal term: {term}")


def validate_docs(manifest: dict[str, Any], failures: list[str]) -> None:
    entries = manifest.get("required_doc_phrases")
    if not isinstance(entries, list):
        return
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            failures.append(f"required_doc_phrases[{index}] must be an object")
            continue
        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value:
            failures.append(f"required_doc_phrases[{index}].path must be a non-empty string")
            continue
        text = read_text(REPO_ROOT / path_value, failures)
        for phrase in string_list(entry.get("phrases"), f"required_doc_phrases[{index}].phrases", failures):
            if not contains_snippet(text, phrase):
                failures.append(f"{path_value} missing observability-readiness phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_signal_groups(manifest, failures)
        validate_docs(manifest, failures)

    if failures:
        print("Observability readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Observability readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
