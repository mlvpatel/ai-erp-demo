#!/usr/bin/env python3
"""Validate intended GitHub repository metadata and community files."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
METADATA = REPO_ROOT / ".github" / "repository-metadata.json"
PUBLIC_POSITIONING = REPO_ROOT / "docs" / "product" / "public-positioning.md"
PUBLICATION_RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "github-publication.md"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

TOPIC_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}$")
FORBIDDEN_DESCRIPTION_CLAIMS = (
    "production-ready",
    "autonomous posting",
    "all industries",
    "all-industry",
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_metadata(failures: list[str]) -> dict[str, Any]:
    try:
        metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(failures, f"missing GitHub metadata: {rel(METADATA)}")
        return {}
    except json.JSONDecodeError as exc:
        fail(failures, f"invalid JSON in {rel(METADATA)}: {exc}")
        return {}
    if metadata.get("schema_version") != 1:
        fail(failures, "repository-metadata schema_version must be 1")
    return metadata


def require_string_list(
    failures: list[str], metadata: dict[str, Any], field: str
) -> list[str]:
    value = metadata.get(field)
    if not isinstance(value, list) or not value:
        fail(failures, f"{field} must be a non-empty list")
        return []
    if any(not isinstance(item, str) or not item.strip() for item in value):
        fail(failures, f"{field} must contain non-empty strings")
        return []
    return value


def validate_description(failures: list[str], metadata: dict[str, Any]) -> None:
    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip():
        fail(failures, "description must be a non-empty string")
        return
    if len(description) > 350:
        fail(failures, "description should be concise enough for GitHub metadata")
    lower = description.lower()
    for claim in FORBIDDEN_DESCRIPTION_CLAIMS:
        if claim in lower:
            fail(failures, f"description must not claim {claim!r}")
    for required in ("ERPNext/Frappe", "service-operations", "human approval"):
        if required not in description:
            fail(failures, f"description should include {required!r}")


def validate_topics(failures: list[str], metadata: dict[str, Any]) -> None:
    topics = require_string_list(failures, metadata, "topics")
    if len(topics) != len(set(topics)):
        fail(failures, "topics must be unique")
    if len(topics) > 20:
        fail(failures, "GitHub allows at most 20 topics")
    for topic in topics:
        if not TOPIC_PATTERN.match(topic):
            fail(failures, f"invalid GitHub topic: {topic}")

    positioning_text = text(PUBLIC_POSITIONING)
    for topic in topics:
        if topic not in positioning_text:
            fail(failures, f"topic {topic!r} must appear in public-positioning suggested topics")


def validate_branch_and_ci(failures: list[str], metadata: dict[str, Any]) -> None:
    default_branch = metadata.get("default_branch")
    if default_branch != "main":
        fail(failures, "default_branch must be main for the first public repo")

    branch_protection = metadata.get("branch_protection")
    if not isinstance(branch_protection, dict):
        fail(failures, "branch_protection must be an object")
        return

    if branch_protection.get("protected_branch") != default_branch:
        fail(failures, "branch_protection.protected_branch must match default_branch")
    for field in ("require_pull_request_reviews", "dismiss_stale_reviews", "restrict_force_pushes"):
        if branch_protection.get(field) is not True:
            fail(failures, f"branch_protection.{field} must be true")

    required_status_checks = branch_protection.get("required_status_checks")
    if not isinstance(required_status_checks, list) or not required_status_checks:
        fail(failures, "branch_protection.required_status_checks must be a non-empty list")
        return
    ci_text = text(CI_WORKFLOW)
    if "branches: [main]" not in ci_text:
        fail(failures, "CI workflow must run on pushes to main")
    for check in required_status_checks:
        if not isinstance(check, str) or not check.strip():
            fail(failures, "required_status_checks must contain non-empty strings")
        elif f"name: {check}" not in ci_text:
            fail(failures, f"required status check not found in CI workflow: {check}")


def validate_features_and_files(failures: list[str], metadata: dict[str, Any]) -> None:
    features = metadata.get("features")
    if not isinstance(features, dict):
        fail(failures, "features must be an object")
    else:
        if features.get("issues") is not True:
            fail(failures, "issues must be enabled for public triage after licensing")
        for field in ("discussions", "wiki", "projects"):
            if features.get(field) is not False:
                fail(failures, f"{field} should remain disabled until maintainers choose otherwise")

    community_files = require_string_list(failures, metadata, "community_files")
    for file_path in community_files:
        if not (REPO_ROOT / file_path).is_file():
            fail(failures, f"community file does not exist: {file_path}")


def validate_release_blockers(failures: list[str], metadata: dict[str, Any]) -> None:
    blockers = require_string_list(failures, metadata, "public_release_blockers")
    blocker_text = " ".join(blockers).lower()
    for required in ("license", "metadata", "artifacts", "local-only", "ci", "fresh clone"):
        if required not in blocker_text:
            fail(failures, f"public_release_blockers must mention {required}")

    runbook_text = text(PUBLICATION_RUNBOOK)
    for phrase in (
        "Confirm the selected AGPL-3.0-only policy remains consistent",
        "Name the initial maintainer",
        "Enable branch protection for `main`",
        "Create or sync labels from `.github/labels.json`",
    ):
        if phrase not in runbook_text:
            fail(failures, f"publication runbook must retain phrase: {phrase!r}")


def main() -> int:
    failures: list[str] = []
    for path in (PUBLIC_POSITIONING, PUBLICATION_RUNBOOK, CI_WORKFLOW):
        if not path.is_file():
            fail(failures, f"required metadata source missing: {rel(path)}")

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
