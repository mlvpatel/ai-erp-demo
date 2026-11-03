"""Helpers shared by the scripts/check-*.py quality gates.

Gates run as `python3 scripts/check-<name>.py`, which puts this directory first
on sys.path, so each gate imports what it needs with `from _gate import ...`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
