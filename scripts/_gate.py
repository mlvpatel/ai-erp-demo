"""Helpers shared by the scripts/check-*.py quality gates.

Gates run as `python3 scripts/check-<name>.py`, which puts this directory first
on sys.path, so each gate imports what it needs with `from _gate import ...`.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json_object(path: Path, failures: list[str]) -> dict[str, Any] | None:
    """Return the JSON object in path, or None after recording why there is none."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"missing JSON file: {rel(path)}")
        return None
    except json.JSONDecodeError as exc:
        failures.append(f"invalid JSON in {rel(path)}: {exc}")
        return None
    if not isinstance(value, dict):
        failures.append(f"{rel(path)} must contain a JSON object")
        return None
    return value


def load_json(path: Path, failures: list[str]) -> dict[str, Any]:
    return load_json_object(path, failures) or {}


def read_text(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        failures.append(f"missing file: {rel(path)}")
    except UnicodeDecodeError as exc:
        failures.append(f"expected UTF-8 text file: {rel(path)}: {exc}")
    return ""


def report(name: str, failures: list[str], passed: str = "") -> int:
    """Print the gate result the same way every gate does and return its exit code."""
    if failures:
        print(f"{name} failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(passed or f"{name} passed.")
    return 0


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


def doc_phrase_entries(
    manifest: dict[str, Any],
    label: str,
    failures: list[str],
    match: Callable[[str, str], bool] = contains_snippet,
) -> None:
    """Check required_doc_phrases given as [{"path": ..., "phrases": [...]}, ...]."""
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
            if not match(text, phrase):
                failures.append(f"{path_value} missing {label} phrase: {phrase}")


def joined_doc_phrases(
    manifest: dict[str, Any], doc_fields: tuple[str, ...], label: str, failures: list[str]
) -> None:
    """Check that each required_doc_phrases entry appears in the docs named by doc_fields."""
    doc_text = "\n".join(
        read_text(REPO_ROOT / path_value, failures)
        for path_value in (manifest.get(field) for field in doc_fields)
        if isinstance(path_value, str)
    )
    for phrase in string_list(manifest.get("required_doc_phrases"), "required_doc_phrases", failures):
        if not contains_snippet(doc_text, phrase):
            failures.append(f"{label} docs missing phrase: {phrase}")


def parse_python(path: Path, failures: list[str]) -> ast.Module | None:
    source = read_text(path, failures)
    if not source:
        return None
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        failures.append(f"invalid Python in {rel(path)}: {exc}")
        return None


def dev_commands(dev_text: str) -> set[str]:
    commands = set(re.findall(r"^\s{2}([a-z][a-z0-9-]*)\s", dev_text, flags=re.MULTILINE))
    case_labels = set(re.findall(r"^\s{2}([a-z][a-z0-9-]*)\)", dev_text, flags=re.MULTILINE))
    return commands | case_labels


def acceptance_claim_ids(manifest: dict[str, Any], failures: list[str]) -> set[str]:
    path_value = manifest.get("mvp_acceptance")
    if not isinstance(path_value, str):
        return set()
    value = load_json_object(REPO_ROOT / path_value, failures)
    if not isinstance(value, dict):
        return set()
    claims = value.get("claims")
    if not isinstance(claims, list):
        failures.append(f"{path_value}: claims must be a list")
        return set()
    return {
        claim["id"]
        for claim in claims
        if isinstance(claim, dict) and isinstance(claim.get("id"), str)
    }
