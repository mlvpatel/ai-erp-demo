#!/usr/bin/env python3
"""Validate tenant/site isolation guardrails for the AI ERP Demo."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "tenant-isolation.json"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path, failures: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"missing JSON file: {rel(path)}")
    except json.JSONDecodeError as exc:
        failures.append(f"invalid JSON in {rel(path)}: {exc}")
    return None


def read_text(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        failures.append(f"missing file: {rel(path)}")
        return ""


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
    for field in (
        "adr",
        "workflow_doc",
        "threat_model",
        "system_boundaries",
        "mvp_blueprint_review",
        "ai_control_plane_readme",
    ):
        required_path(manifest, field, failures)

    for field in ("source_anchors", "required_doc_phrases", "forbidden_source_terms"):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            failures.append(f"{field} must be a non-empty list")


def validate_source_anchors(manifest: dict[str, Any], failures: list[str]) -> None:
    seen_ids: set[str] = set()
    for index, anchor in enumerate(manifest.get("source_anchors", []), 1):
        if not isinstance(anchor, dict):
            failures.append(f"source_anchors[{index}] must be an object")
            continue
        anchor_id = anchor.get("id")
        if not isinstance(anchor_id, str) or not anchor_id:
            failures.append(f"source_anchors[{index}].id must be a non-empty string")
            anchor_id = f"source_anchors[{index}]"
        elif anchor_id in seen_ids:
            failures.append(f"{anchor_id}: duplicate source anchor id")
        seen_ids.add(str(anchor_id))

        path_value = anchor.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            failures.append(f"{anchor_id}: path must be a non-empty string")
            continue
        source_text = read_text(REPO_ROOT / path_value, failures)
        for snippet in string_list(anchor.get("required_snippets"), f"{anchor_id}.required_snippets", failures):
            if not contains_snippet(source_text, snippet):
                failures.append(f"{anchor_id}: {path_value} missing snippet: {snippet}")


def validate_docs(manifest: dict[str, Any], failures: list[str]) -> None:
    doc_text = "\n".join(
        read_text(REPO_ROOT / path_value, failures)
        for path_value in (
            manifest.get("adr"),
            manifest.get("workflow_doc"),
            manifest.get("threat_model"),
            manifest.get("system_boundaries"),
            manifest.get("mvp_blueprint_review"),
            manifest.get("ai_control_plane_readme"),
        )
        if isinstance(path_value, str)
    )
    for phrase in string_list(manifest.get("required_doc_phrases"), "required_doc_phrases", failures):
        if not contains_snippet(doc_text, phrase):
            failures.append(f"tenant isolation docs missing phrase: {phrase}")


def iter_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return [
        child
        for child in path.rglob("*")
        if child.is_file()
        and "__pycache__" not in child.parts
        and "development" not in child.parts
    ]


def validate_forbidden_source_terms(manifest: dict[str, Any], failures: list[str]) -> None:
    for index, entry in enumerate(manifest.get("forbidden_source_terms", []), 1):
        if not isinstance(entry, dict):
            failures.append(f"forbidden_source_terms[{index}] must be an object")
            continue
        term = entry.get("term")
        if not isinstance(term, str) or not term:
            failures.append(f"forbidden_source_terms[{index}].term must be a non-empty string")
            continue
        for path_value in string_list(entry.get("paths"), f"forbidden_source_terms[{index}].paths", failures):
            root = REPO_ROOT / path_value
            if not root.exists():
                failures.append(f"forbidden term path is missing: {path_value}")
                continue
            for candidate in iter_files(root):
                try:
                    text = candidate.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                if term in text:
                    failures.append(f"{rel(candidate)} contains forbidden tenant shortcut {term!r}")


def main() -> int:
    failures: list[str] = []
    value = load_json(MANIFEST_PATH, failures)
    manifest = value if isinstance(value, dict) else {}

    if manifest:
        validate_shape(manifest, failures)
        validate_source_anchors(manifest, failures)
        validate_docs(manifest, failures)
        validate_forbidden_source_terms(manifest, failures)

    if failures:
        print("Tenant isolation check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Tenant isolation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
