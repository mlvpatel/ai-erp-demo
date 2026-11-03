#!/usr/bin/env python3
"""Validate release and versioning policy consistency."""

from __future__ import annotations

from typing import Any

from _gate import REPO_ROOT, contains_snippet, load_json, read_text, report, string_list


MANIFEST_PATH = REPO_ROOT / "config" / "release-policy.json"


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

    return report("Release policy check", failures)


if __name__ == "__main__":
    raise SystemExit(main())
