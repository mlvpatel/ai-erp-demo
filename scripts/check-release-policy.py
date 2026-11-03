#!/usr/bin/env python3
"""Validate release and versioning policy consistency."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "release-policy.json"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"missing JSON file: {rel(path)}")
        return {}
    except json.JSONDecodeError as exc:
        failures.append(f"invalid JSON in {rel(path)}: {exc}")
        return {}
    if not isinstance(value, dict):
        failures.append(f"{rel(path)} must contain a JSON object")
        return {}
    return value


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


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    for field in (
        "policy_doc",
        "changelog",
        "publication_runbook",
        "public_positioning_doc",
    ):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{field} must be a non-empty string")
        elif not (REPO_ROOT / value).is_file():
            failures.append(f"{field} path is missing: {value}")

    for field in (
        "required_release_commands",
        "required_policy_phrases",
        "required_changelog_phrases",
        "forbidden_public_claims_before_1_0",
    ):
        string_list(manifest.get(field), field, failures)


def validate_docs(manifest: dict[str, Any], failures: list[str]) -> None:
    policy_doc = manifest.get("policy_doc")
    changelog = manifest.get("changelog")
    publication_runbook = manifest.get("publication_runbook")
    public_positioning_doc = manifest.get("public_positioning_doc")
    if not all(isinstance(path, str) for path in (policy_doc, changelog, publication_runbook, public_positioning_doc)):
        return

    policy_text = read_text(REPO_ROOT / str(policy_doc), failures)
    changelog_text = read_text(REPO_ROOT / str(changelog), failures)
    runbook_text = read_text(REPO_ROOT / str(publication_runbook), failures)
    positioning_text = read_text(REPO_ROOT / str(public_positioning_doc), failures)

    for phrase in string_list(manifest.get("required_policy_phrases"), "required_policy_phrases", failures):
        if not contains_snippet(policy_text, phrase):
            failures.append(f"{policy_doc}: missing required release-policy phrase: {phrase}")

    for phrase in string_list(manifest.get("required_changelog_phrases"), "required_changelog_phrases", failures):
        if not contains_snippet(changelog_text, phrase):
            failures.append(f"{changelog}: missing required changelog phrase: {phrase}")

    for command in string_list(manifest.get("required_release_commands"), "required_release_commands", failures):
        if not contains_snippet(policy_text, command):
            failures.append(f"{policy_doc}: missing release command: {command}")
        if command != "scripts/check-publication-source.sh --strict" and not contains_snippet(runbook_text, command):
            failures.append(f"{publication_runbook}: missing release command: {command}")

    for claim in string_list(
        manifest.get("forbidden_public_claims_before_1_0"),
        "forbidden_public_claims_before_1_0",
        failures,
    ):
        if not contains_snippet(policy_text, claim):
            failures.append(f"{policy_doc}: missing forbidden pre-1.0 claim warning: {claim}")
        if not contains_snippet(positioning_text, claim):
            failures.append(f"{public_positioning_doc}: missing public-positioning claim warning: {claim}")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_docs(manifest, failures)

    if failures:
        print("Release policy check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Release policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
