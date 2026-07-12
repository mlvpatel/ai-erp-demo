#!/usr/bin/env python3
"""Validate operations, recovery, and incident-response guardrails."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "operations-readiness.json"


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
        fail(failures, "operations-readiness.json schema_version must be 1")
    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        fail(failures, "description must be a non-empty string")

    for field in (
        "workflow_doc",
        "backup_restore_runbook",
        "incident_response_runbook",
        "support_doc",
        "security_policy",
        "data_classification_doc",
        "release_process_doc",
        "github_publication_runbook",
        "quality_gates_doc",
        "traceability_doc",
        "publication_scan_manifest",
        "gitignore",
        "gitattributes",
        "publication_source_script",
    ):
        required_path(manifest, field, failures)

    for field in (
        "required_gitignore_patterns",
        "required_export_ignore_patterns",
        "required_publication_source_snippets",
        "publication_scan_required_exclusions",
        "required_doc_phrases",
    ):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            fail(failures, f"{field} must be a non-empty list")


def validate_gitignore(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("gitignore")
    if not isinstance(path_value, str):
        return
    text = read_text(REPO_ROOT / path_value, failures)
    lines = {line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")}
    for pattern in string_list(manifest.get("required_gitignore_patterns"), "required_gitignore_patterns", failures):
        if pattern not in lines:
            fail(failures, f"{path_value} missing local/recovery artifact pattern: {pattern}")


def export_ignore_pattern_present(text: str, pattern: str) -> bool:
    escaped = re.escape(pattern)
    return re.search(rf"^{escaped}\s+export-ignore(?:\s|$)", text, flags=re.MULTILINE) is not None


def validate_gitattributes(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("gitattributes")
    if not isinstance(path_value, str):
        return
    text = read_text(REPO_ROOT / path_value, failures)
    for pattern in string_list(
        manifest.get("required_export_ignore_patterns"),
        "required_export_ignore_patterns",
        failures,
    ):
        if not export_ignore_pattern_present(text, pattern):
            fail(failures, f"{path_value} must export-ignore local/recovery artifact pattern: {pattern}")


def validate_publication_source_script(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("publication_source_script")
    if not isinstance(path_value, str):
        return
    text = read_text(REPO_ROOT / path_value, failures)
    for snippet in string_list(
        manifest.get("required_publication_source_snippets"),
        "required_publication_source_snippets",
        failures,
    ):
        if snippet not in text:
            fail(failures, f"{path_value} missing publication-source exclusion: {snippet}")


def validate_publication_scan_manifest(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("publication_scan_manifest")
    if not isinstance(path_value, str):
        return
    value = load_json(REPO_ROOT / path_value, failures)
    if not isinstance(value, dict):
        return

    searchable_fields = (
        "excluded_path_prefixes",
        "forbidden_tracked_path_prefixes",
        "forbidden_tracked_path_suffixes",
        "required_local_only_exclusions",
    )
    configured: set[str] = set()
    for field in searchable_fields:
        field_value = value.get(field)
        if isinstance(field_value, list):
            configured.update(item for item in field_value if isinstance(item, str))

    for pattern in string_list(
        manifest.get("publication_scan_required_exclusions"),
        "publication_scan_required_exclusions",
        failures,
    ):
        if pattern not in configured:
            fail(failures, f"{path_value} missing publication scan exclusion: {pattern}")


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
                fail(failures, f"{path_value} missing operations-readiness phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    value = load_json(MANIFEST_PATH, failures)
    manifest = value if isinstance(value, dict) else {}

    if manifest:
        validate_shape(manifest, failures)
        validate_gitignore(manifest, failures)
        validate_gitattributes(manifest, failures)
        validate_publication_source_script(manifest, failures)
        validate_publication_scan_manifest(manifest, failures)
        validate_docs(manifest, failures)

    if failures:
        print("Operations readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Operations readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
