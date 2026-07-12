#!/usr/bin/env python3
"""Validate observability and alerting readiness guardrails."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "observability-readiness.json"


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
        fail(failures, "observability-readiness.json schema_version must be 1")
    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        fail(failures, "description must be a non-empty string")

    for field in (
        "workflow_doc",
        "infra_readme",
        "alert_rules_example",
        "operations_readiness_doc",
        "incident_response_runbook",
        "backup_restore_runbook",
        "data_classification_doc",
        "threat_model",
        "github_publication_runbook",
        "quality_gates_doc",
        "traceability_doc",
    ):
        required_path(manifest, field, failures)

    for field in (
        "signal_groups",
        "required_alerts",
        "forbidden_observability_snippets",
        "required_doc_phrases",
    ):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            fail(failures, f"{field} must be a non-empty list")


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
            fail(failures, f"signal_groups[{index}] must be an object")
            continue
        group_id = group.get("id")
        if not isinstance(group_id, str) or not group_id.strip():
            fail(failures, f"signal_groups[{index}].id must be a non-empty string")
        elif group_id in seen:
            fail(failures, f"duplicate signal group id: {group_id}")
        else:
            seen.add(group_id)
        for term in string_list(group.get("required_terms"), f"signal_groups[{index}].required_terms", failures):
            if not contains_snippet(workflow_text, term):
                fail(failures, f"{workflow_path} missing signal term: {term}")


def validate_alert_rules(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("alert_rules_example")
    if not isinstance(path_value, str):
        return
    text = read_text(REPO_ROOT / path_value, failures)
    for alert in string_list(manifest.get("required_alerts"), "required_alerts", failures):
        if not contains_snippet(text, f"alert: {alert}"):
            fail(failures, f"{path_value} missing alert rule: {alert}")

    lower_text = text.lower()
    for snippet in string_list(
        manifest.get("forbidden_observability_snippets"),
        "forbidden_observability_snippets",
        failures,
    ):
        if snippet.lower() in lower_text:
            fail(failures, f"{path_value} contains forbidden observability snippet: {snippet}")


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
                fail(failures, f"{path_value} missing observability-readiness phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    value = load_json(MANIFEST_PATH, failures)
    manifest = value if isinstance(value, dict) else {}

    if manifest:
        validate_shape(manifest, failures)
        validate_signal_groups(manifest, failures)
        validate_alert_rules(manifest, failures)
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
