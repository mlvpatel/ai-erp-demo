#!/usr/bin/env python3
"""Validate observability and alerting readiness guardrails."""

from __future__ import annotations

from typing import Any

from _gate import (
    REPO_ROOT,
    contains_snippet,
    doc_phrase_entries,
    load_json,
    read_text,
    report,
    required_path,
    string_list,
)


MANIFEST_PATH = REPO_ROOT / "config" / "observability-readiness.json"


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


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_signal_groups(manifest, failures)
        doc_phrase_entries(manifest, "observability-readiness", failures)

    return report("Observability readiness check", failures)


if __name__ == "__main__":
    raise SystemExit(main())
