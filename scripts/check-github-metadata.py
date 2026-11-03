#!/usr/bin/env python3
"""Validate intended GitHub repository metadata and community files."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

from _gate import REPO_ROOT, read_text, rel


METADATA = REPO_ROOT / ".github" / "repository-metadata.json"
PUBLIC_POSITIONING = REPO_ROOT / "docs" / "product" / "public-positioning.md"
PUBLICATION_RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "github-publication.md"

TOPIC_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}$")
FORBIDDEN_DESCRIPTION_CLAIMS = (
    "production-ready",
    "autonomous posting",
    "all industries",
    "all-industry",
)


def load_metadata(failures: list[str]) -> dict[str, Any]:
    try:
        metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"missing GitHub metadata: {rel(METADATA)}")
        return {}
    except json.JSONDecodeError as exc:
        failures.append(f"invalid JSON in {rel(METADATA)}: {exc}")
        return {}
    if metadata.get("schema_version") != 1:
        failures.append("repository-metadata schema_version must be 1")
    return metadata


def require_string_list(
    failures: list[str], metadata: dict[str, Any], field: str
) -> list[str]:
    value = metadata.get(field)
    if not isinstance(value, list) or not value:
        failures.append(f"{field} must be a non-empty list")
        return []
    if any(not isinstance(item, str) or not item.strip() for item in value):
        failures.append(f"{field} must contain non-empty strings")
        return []
    return value


def validate_description(failures: list[str], metadata: dict[str, Any]) -> None:
    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip():
        failures.append("description must be a non-empty string")
        return
    if len(description) > 350:
        failures.append("description should be concise enough for GitHub metadata")
    lower = description.lower()
    for claim in FORBIDDEN_DESCRIPTION_CLAIMS:
        if claim in lower:
            failures.append(f"description must not claim {claim!r}")
    for required in ("ERPNext/Frappe", "service-operations", "human approval"):
        if required not in description:
            failures.append(f"description should include {required!r}")


def validate_topics(failures: list[str], metadata: dict[str, Any]) -> None:
    topics = require_string_list(failures, metadata, "topics")
    if len(topics) != len(set(topics)):
        failures.append("topics must be unique")
    if len(topics) > 20:
        failures.append("GitHub allows at most 20 topics")
    for topic in topics:
        if not TOPIC_PATTERN.match(topic):
            failures.append(f"invalid GitHub topic: {topic}")

    positioning_text = read_text(PUBLIC_POSITIONING, failures)
    for topic in topics:
        if topic not in positioning_text:
            failures.append(f"topic {topic!r} must appear in public-positioning suggested topics")


def validate_branch_and_ci(failures: list[str], metadata: dict[str, Any]) -> None:
    default_branch = metadata.get("default_branch")
    if default_branch != "main":
        failures.append("default_branch must be main for the first public repo")

    branch_protection = metadata.get("branch_protection")
    if not isinstance(branch_protection, dict):
        failures.append("branch_protection must be an object")
        return

    if branch_protection.get("protected_branch") != default_branch:
        failures.append("branch_protection.protected_branch must match default_branch")
    for field in ("require_pull_request_reviews", "dismiss_stale_reviews", "restrict_force_pushes"):
        if branch_protection.get(field) is not True:
            failures.append(f"branch_protection.{field} must be true")


def validate_features_and_files(failures: list[str], metadata: dict[str, Any]) -> None:
    features = metadata.get("features")
    if not isinstance(features, dict):
        failures.append("features must be an object")
    else:
        if features.get("issues") is not True:
            failures.append("issues must be enabled for public triage after licensing")
        for field in ("discussions", "wiki", "projects"):
            if features.get(field) is not False:
                failures.append(f"{field} should remain disabled until maintainers choose otherwise")

    community_files = require_string_list(failures, metadata, "community_files")
    for file_path in community_files:
        if not (REPO_ROOT / file_path).is_file():
            failures.append(f"community file does not exist: {file_path}")


def validate_release_blockers(failures: list[str], metadata: dict[str, Any]) -> None:
    blockers = require_string_list(failures, metadata, "public_release_blockers")
    blocker_text = " ".join(blockers).lower()
    for required in ("license", "metadata", "artifacts", "local-only", "ci", "fresh clone"):
        if required not in blocker_text:
            failures.append(f"public_release_blockers must mention {required}")

    runbook_text = read_text(PUBLICATION_RUNBOOK, failures)
    for phrase in (
        "Confirm the selected AGPL-3.0-only policy remains consistent",
        "Name the initial maintainer",
        "Enable branch protection for `main`",
        "Create or sync labels from `.github/labels.json`",
    ):
        if phrase not in runbook_text:
            failures.append(f"publication runbook must retain phrase: {phrase!r}")


def main() -> int:
    failures: list[str] = []
    for path in (PUBLIC_POSITIONING, PUBLICATION_RUNBOOK):
        if not path.is_file():
            failures.append(f"required metadata source missing: {rel(path)}")

    metadata = load_metadata(failures)
    if metadata and not failures:
        validate_description(failures, metadata)
        validate_topics(failures, metadata)
        validate_branch_and_ci(failures, metadata)
        validate_features_and_files(failures, metadata)
        validate_release_blockers(failures, metadata)

    if failures:
        print("GitHub metadata check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("GitHub metadata check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
