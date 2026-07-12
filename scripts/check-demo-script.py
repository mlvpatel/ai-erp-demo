#!/usr/bin/env python3
"""Validate the public demo script against MVP evidence and safety rules."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "demo-script.json"
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


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


def dev_commands(dev_text: str) -> set[str]:
    commands = set(re.findall(r"^\s{2}([a-z][a-z0-9-]*)\s", dev_text, flags=re.MULTILINE))
    case_labels = set(re.findall(r"^\s{2}([a-z][a-z0-9-]*)\)", dev_text, flags=re.MULTILINE))
    return commands | case_labels


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    if manifest.get("schema_version") != 1:
        fail(failures, "demo-script.json schema_version must be 1")
    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        fail(failures, "description must be a non-empty string")

    for field in (
        "script_doc",
        "local_demo_runbook",
        "readme",
        "backlog",
        "dev_helper",
        "mvp_acceptance",
        "first_public_issues",
    ):
        required_path(manifest, field, failures)

    for field in (
        "required_dev_commands",
        "story_beats",
        "required_safety_phrases",
        "required_readme_phrases",
        "required_runbook_phrases",
        "required_backlog_phrases",
    ):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            fail(failures, f"{field} must be a non-empty list")

    if not isinstance(manifest.get("first_public_issue_id"), str) or not manifest["first_public_issue_id"].strip():
        fail(failures, "first_public_issue_id must be a non-empty string")


def validate_commands(manifest: dict[str, Any], failures: list[str]) -> None:
    script_path = manifest.get("script_doc")
    dev_path = manifest.get("dev_helper")
    script_text = read_text(REPO_ROOT / script_path, failures) if isinstance(script_path, str) else ""
    dev_text = read_text(REPO_ROOT / dev_path, failures) if isinstance(dev_path, str) else ""
    commands = dev_commands(dev_text)

    for command in string_list(manifest.get("required_dev_commands"), "required_dev_commands", failures):
        if command not in commands:
            fail(failures, f"scripts/dev.sh must implement/document demo command: {command}")
        if f"{command})" not in dev_text:
            fail(failures, f"scripts/dev.sh missing case branch for demo command: {command}")
        expected = f"scripts/dev.sh {command}"
        if expected not in script_text:
            fail(failures, f"{script_path} must mention {expected}")


def acceptance_claim_ids(manifest: dict[str, Any], failures: list[str]) -> set[str]:
    path_value = manifest.get("mvp_acceptance")
    if not isinstance(path_value, str):
        return set()
    value = load_json(REPO_ROOT / path_value, failures)
    if not isinstance(value, dict):
        return set()
    claims = value.get("claims")
    if not isinstance(claims, list):
        fail(failures, f"{path_value}: claims must be a list")
        return set()
    return {
        claim["id"]
        for claim in claims
        if isinstance(claim, dict) and isinstance(claim.get("id"), str)
    }


def validate_story_beats(manifest: dict[str, Any], failures: list[str]) -> None:
    script_path = manifest.get("script_doc")
    script_text = read_text(REPO_ROOT / script_path, failures) if isinstance(script_path, str) else ""
    claim_ids = acceptance_claim_ids(manifest, failures)
    seen_ids: set[str] = set()

    for index, beat in enumerate(manifest.get("story_beats", []), 1):
        if not isinstance(beat, dict):
            fail(failures, f"story_beats[{index}] must be an object")
            continue
        beat_id = beat.get("id")
        if not isinstance(beat_id, str) or not ID_PATTERN.match(beat_id):
            fail(failures, f"story_beats[{index}].id must be kebab-case")
            beat_id = f"story_beats[{index}]"
        elif beat_id in seen_ids:
            fail(failures, f"{beat_id}: duplicate story beat id")
        seen_ids.add(str(beat_id))

        title = beat.get("title")
        if not isinstance(title, str) or not title.strip():
            fail(failures, f"{beat_id}: title must be non-empty")
        elif title not in script_text:
            fail(failures, f"{beat_id}: script doc missing title: {title}")

        for claim_id in string_list(beat.get("acceptance_claims"), f"{beat_id}.acceptance_claims", failures):
            if claim_id not in claim_ids:
                fail(failures, f"{beat_id}: acceptance claim is missing from config/mvp-acceptance.json: {claim_id}")
            if claim_id not in script_text:
                fail(failures, f"{beat_id}: script doc must mention acceptance claim {claim_id}")

        for phrase in string_list(beat.get("required_phrases"), f"{beat_id}.required_phrases", failures):
            if not contains_snippet(script_text, phrase):
                fail(failures, f"{beat_id}: script doc missing phrase: {phrase}")

        for evidence in string_list(beat.get("evidence_paths"), f"{beat_id}.evidence_paths", failures):
            if not (REPO_ROOT / evidence).exists():
                fail(failures, f"{beat_id}: evidence path does not exist: {evidence}")


def validate_doc_phrases(manifest: dict[str, Any], failures: list[str]) -> None:
    path_fields = {
        "script_doc": "required_safety_phrases",
        "readme": "required_readme_phrases",
        "local_demo_runbook": "required_runbook_phrases",
        "backlog": "required_backlog_phrases",
    }
    for path_field, phrase_field in path_fields.items():
        path_value = manifest.get(path_field)
        text = read_text(REPO_ROOT / path_value, failures) if isinstance(path_value, str) else ""
        for phrase in string_list(manifest.get(phrase_field), phrase_field, failures):
            if not contains_snippet(text, phrase):
                fail(failures, f"{path_value} missing demo-script phrase: {phrase}")


def validate_first_public_issue(manifest: dict[str, Any], failures: list[str]) -> None:
    issues_path = manifest.get("first_public_issues")
    script_doc = manifest.get("script_doc")
    issue_id = manifest.get("first_public_issue_id")
    if not isinstance(issues_path, str) or not isinstance(script_doc, str) or not isinstance(issue_id, str):
        return

    value = load_json(REPO_ROOT / issues_path, failures)
    if not isinstance(value, dict):
        return
    issues = value.get("issues")
    if not isinstance(issues, list):
        fail(failures, f"{issues_path}: issues must be a list")
        return
    issue = next(
        (item for item in issues if isinstance(item, dict) and item.get("id") == issue_id),
        None,
    )
    if issue is None:
        fail(failures, f"{issues_path}: missing first public demo issue {issue_id}")
        return
    evidence_paths = issue.get("evidence_paths")
    if not isinstance(evidence_paths, list) or script_doc not in evidence_paths:
        fail(failures, f"{issue_id}: evidence_paths must include {script_doc}")
    checks = issue.get("acceptance_checks")
    check_text = json.dumps(checks, sort_keys=True)
    if "demo script" not in check_text.lower():
        fail(failures, f"{issue_id}: acceptance checks must mention the demo script")


def main() -> int:
    failures: list[str] = []
    value = load_json(MANIFEST_PATH, failures)
    manifest = value if isinstance(value, dict) else {}

    if manifest:
        validate_shape(manifest, failures)
        validate_commands(manifest, failures)
        validate_story_beats(manifest, failures)
        validate_doc_phrases(manifest, failures)
        validate_first_public_issue(manifest, failures)

    if failures:
        print("Demo script check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Demo script check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
