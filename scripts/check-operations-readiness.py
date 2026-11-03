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
GITIGNORE = REPO_ROOT / ".gitignore"
GITATTRIBUTES = REPO_ROOT / ".gitattributes"
PUBLICATION_SOURCE_SCRIPT = REPO_ROOT / "scripts" / "check-publication-source.sh"


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
    except UnicodeDecodeError as exc:
        failures.append(f"expected UTF-8 text file: {rel(path)}: {exc}")
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


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    for field in (
        "local_artifact_patterns",
        "local_ignore_patterns",
        "required_doc_phrases",
    ):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            failures.append(f"{field} must be a non-empty list")


def validate_local_artifacts(manifest: dict[str, Any], failures: list[str]) -> None:
    """local_artifact_patterns must be in .gitignore, export-ignored, and excluded by the
    publication-source find; local_ignore_patterns only need the first two. A `!name`
    entry re-includes a file, so .gitattributes must mark it `name -export-ignore`."""
    shared = string_list(manifest.get("local_artifact_patterns"), "local_artifact_patterns", failures)
    ignore_only = string_list(manifest.get("local_ignore_patterns"), "local_ignore_patterns", failures)
    gitignore_text = read_text(GITIGNORE, failures)
    gitignore = {line.strip() for line in gitignore_text.splitlines() if line.strip() and not line.strip().startswith("#")}
    gitattributes = read_text(GITATTRIBUTES, failures)
    source_script = read_text(PUBLICATION_SOURCE_SCRIPT, failures)
    for pattern in shared + ignore_only:
        if pattern not in gitignore:
            failures.append(f".gitignore missing local/recovery artifact pattern: {pattern}")
        attribute = f"{re.escape(pattern[1:])}\\s+-export-ignore" if pattern.startswith("!") else f"{re.escape(pattern)}\\s+export-ignore"
        if not re.search(rf"^{attribute}(?:\s|$)", gitattributes, flags=re.MULTILINE):
            failures.append(f".gitattributes missing export rule for local/recovery artifact pattern: {pattern}")
    for pattern in shared:
        clause = f"-name '{pattern}'" if "*" in pattern else f"-path './{pattern.rstrip('/')}'"
        if clause not in source_script:
            failures.append(f"{rel(PUBLICATION_SOURCE_SCRIPT)} missing publication-source exclusion: {clause}")


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
                failures.append(f"{path_value} missing operations-readiness phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    value = load_json(MANIFEST_PATH, failures)
    manifest = value if isinstance(value, dict) else {}

    if manifest:
        validate_shape(manifest, failures)
        validate_local_artifacts(manifest, failures)
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
