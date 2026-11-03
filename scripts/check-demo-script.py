#!/usr/bin/env python3
"""Validate the public demo script against MVP evidence and safety rules."""

from __future__ import annotations

import re
from typing import Any

from _gate import (
    REPO_ROOT,
    acceptance_claim_ids,
    contains_snippet,
    dev_commands,
    load_json,
    read_text,
    report,
    required_path,
    string_list,
)


MANIFEST_PATH = REPO_ROOT / "config" / "demo-script.json"
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    for field in (
        "script_doc",
        "local_demo_runbook",
        "readme",
        "backlog",
        "dev_helper",
        "mvp_acceptance",
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
            failures.append(f"{field} must be a non-empty list")


def validate_commands(manifest: dict[str, Any], failures: list[str]) -> None:
    script_path = manifest.get("script_doc")
    dev_path = manifest.get("dev_helper")
    script_text = read_text(REPO_ROOT / script_path, failures) if isinstance(script_path, str) else ""
    dev_text = read_text(REPO_ROOT / dev_path, failures) if isinstance(dev_path, str) else ""
    commands = dev_commands(dev_text)

    for command in string_list(manifest.get("required_dev_commands"), "required_dev_commands", failures):
        if command not in commands:
            failures.append(f"scripts/dev.sh must implement/document demo command: {command}")
        if f"{command})" not in dev_text:
            failures.append(f"scripts/dev.sh missing case branch for demo command: {command}")
        expected = f"scripts/dev.sh {command}"
        if expected not in script_text:
            failures.append(f"{script_path} must mention {expected}")


def validate_story_beats(manifest: dict[str, Any], failures: list[str]) -> None:
    script_path = manifest.get("script_doc")
    script_text = read_text(REPO_ROOT / script_path, failures) if isinstance(script_path, str) else ""
    claim_ids = acceptance_claim_ids(manifest, failures)
    seen_ids: set[str] = set()

    for index, beat in enumerate(manifest.get("story_beats", []), 1):
        if not isinstance(beat, dict):
            failures.append(f"story_beats[{index}] must be an object")
            continue
        beat_id = beat.get("id")
        if not isinstance(beat_id, str) or not ID_PATTERN.match(beat_id):
            failures.append(f"story_beats[{index}].id must be kebab-case")
            beat_id = f"story_beats[{index}]"
        elif beat_id in seen_ids:
            failures.append(f"{beat_id}: duplicate story beat id")
        seen_ids.add(str(beat_id))

        title = beat.get("title")
        if not isinstance(title, str) or not title.strip():
            failures.append(f"{beat_id}: title must be non-empty")
        elif title not in script_text:
            failures.append(f"{beat_id}: script doc missing title: {title}")

        for claim_id in string_list(beat.get("acceptance_claims"), f"{beat_id}.acceptance_claims", failures):
            if claim_id not in claim_ids:
                failures.append(f"{beat_id}: acceptance claim is missing from config/mvp-acceptance.json: {claim_id}")
            if claim_id not in script_text:
                failures.append(f"{beat_id}: script doc must mention acceptance claim {claim_id}")

        for phrase in string_list(beat.get("required_phrases"), f"{beat_id}.required_phrases", failures):
            if not contains_snippet(script_text, phrase):
                failures.append(f"{beat_id}: script doc missing phrase: {phrase}")

        for evidence in string_list(beat.get("evidence_paths"), f"{beat_id}.evidence_paths", failures):
            if not (REPO_ROOT / evidence).exists():
                failures.append(f"{beat_id}: evidence path does not exist: {evidence}")


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
                failures.append(f"{path_value} missing demo-script phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_commands(manifest, failures)
        validate_story_beats(manifest, failures)
        validate_doc_phrases(manifest, failures)

    return report("Demo script check", failures)


if __name__ == "__main__":
    raise SystemExit(main())
