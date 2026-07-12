#!/usr/bin/env python3
"""Validate the first public GitHub issue manifest.

The manifest is a launch checklist, not an API client. It keeps early public
issues small, reviewable, and away from ERP/AI safety boundaries until the root
license and release-readiness gates are resolved.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
ISSUES_FILE = REPO_ROOT / "config" / "first-public-issues.json"
LABELS_FILE = REPO_ROOT / ".github" / "labels.json"

ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FORBIDDEN_STARTER_LABELS = {
    "ai-safety",
    "blocked-license",
    "contract",
    "dependency",
    "erp-safety",
    "industry-pack",
    "security",
}
SAFE_STARTER_AREAS = {"documentation", "developer tooling"}
FORBIDDEN_TITLE_PHRASES = {
    "all industries",
    "autonomous",
    "production-ready",
    "post invoice",
    "submit invoice",
    "post stock",
    "change permissions",
    "payroll",
}
REQUIRED_PUBLICATION_GATES = {
    "root-license-resolved",
    "release-readiness-passed",
    "maintainer-review-before-creation",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def load_json(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(failures, f"missing JSON file: {rel(path)}")
        return {}
    except json.JSONDecodeError as exc:
        fail(failures, f"invalid JSON in {rel(path)}: {exc}")
        return {}

    if not isinstance(value, dict):
        fail(failures, f"{rel(path)} must contain a JSON object")
        return {}
    return value


def label_names(failures: list[str]) -> set[str]:
    manifest = load_json(LABELS_FILE, failures)
    labels = manifest.get("labels", [])
    if not isinstance(labels, list):
        fail(failures, ".github/labels.json labels must be a list")
        return set()

    names: set[str] = set()
    for index, label in enumerate(labels, 1):
        if not isinstance(label, dict) or not isinstance(label.get("name"), str):
            fail(failures, f".github/labels.json labels[{index}] must have a name")
            continue
        names.add(label["name"])
    return names


def validate_command(issue_id: str, index: int, check: dict[str, Any], failures: list[str]) -> None:
    command = check.get("command")
    if not isinstance(command, str) or not command.strip():
        fail(failures, f"{issue_id}: acceptance_checks[{index}] command must be non-empty")
        return

    first_token = command.split()[0]
    if first_token.startswith("scripts/") and not (REPO_ROOT / first_token).is_file():
        fail(failures, f"{issue_id}: command references missing script: {first_token}")


def validate_acceptance_checks(issue: dict[str, Any], failures: list[str]) -> None:
    issue_id = str(issue.get("id", "<missing-id>"))
    checks = issue.get("acceptance_checks")
    if not isinstance(checks, list) or not checks:
        fail(failures, f"{issue_id}: acceptance_checks must be a non-empty list")
        return

    for index, check in enumerate(checks, 1):
        if not isinstance(check, dict):
            fail(failures, f"{issue_id}: acceptance_checks[{index}] must be an object")
            continue
        check_type = check.get("type")
        if check_type == "command":
            validate_command(issue_id, index, check, failures)
        elif check_type == "review":
            description = check.get("description")
            if not isinstance(description, str) or not description.strip():
                fail(failures, f"{issue_id}: review check {index} needs a description")
        else:
            fail(failures, f"{issue_id}: unsupported acceptance check type {check_type!r}")


def validate_issue(issue: Any, index: int, labels: set[str], seen_ids: set[str], failures: list[str]) -> None:
    if not isinstance(issue, dict):
        fail(failures, f"issues[{index}] must be an object")
        return

    issue_id = issue.get("id")
    if not isinstance(issue_id, str) or not ID_PATTERN.match(issue_id):
        fail(failures, f"issues[{index}].id must be kebab-case")
        issue_id = f"issues[{index}]"
    elif issue_id in seen_ids:
        fail(failures, f"{issue_id}: duplicate issue id")
    else:
        seen_ids.add(issue_id)

    title = issue.get("title")
    if not isinstance(title, str) or not title.strip():
        fail(failures, f"{issue_id}: title must be non-empty")
    else:
        lowered = title.lower()
        for phrase in sorted(FORBIDDEN_TITLE_PHRASES):
            if phrase in lowered:
                fail(failures, f"{issue_id}: title contains unsafe public-starter phrase {phrase!r}")

    template = issue.get("template")
    if not isinstance(template, str) or not (REPO_ROOT / template).is_file():
        fail(failures, f"{issue_id}: template must point to an existing issue template")

    issue_labels = issue.get("labels")
    if not isinstance(issue_labels, list) or not issue_labels:
        fail(failures, f"{issue_id}: labels must be a non-empty list")
        issue_label_set: set[str] = set()
    else:
        issue_label_set = {label for label in issue_labels if isinstance(label, str)}
        if len(issue_label_set) != len(issue_labels):
            fail(failures, f"{issue_id}: every label must be a string")
        missing = sorted(issue_label_set - labels)
        if missing:
            fail(failures, f"{issue_id}: labels missing from .github/labels.json: {', '.join(missing)}")

    if "good first issue" not in issue_label_set:
        fail(failures, f"{issue_id}: first public issue must include 'good first issue'")

    unsafe_labels = sorted(issue_label_set & FORBIDDEN_STARTER_LABELS)
    if unsafe_labels:
        fail(failures, f"{issue_id}: unsafe labels for a first public issue: {', '.join(unsafe_labels)}")

    area = issue.get("area")
    if area not in SAFE_STARTER_AREAS:
        fail(failures, f"{issue_id}: area must be one of {', '.join(sorted(SAFE_STARTER_AREAS))}")

    if issue.get("safety_class") != "safe-first-issue":
        fail(failures, f"{issue_id}: safety_class must be safe-first-issue")

    evidence_paths = issue.get("evidence_paths")
    if not isinstance(evidence_paths, list) or not evidence_paths:
        fail(failures, f"{issue_id}: evidence_paths must be a non-empty list")
    else:
        for evidence in evidence_paths:
            if not isinstance(evidence, str):
                fail(failures, f"{issue_id}: every evidence path must be a string")
            elif not (REPO_ROOT / evidence).exists():
                fail(failures, f"{issue_id}: evidence path does not exist: {evidence}")

    validate_acceptance_checks(issue, failures)


def main() -> int:
    failures: list[str] = []
    labels = label_names(failures)
    manifest = load_json(ISSUES_FILE, failures)

    if manifest.get("schema_version") != 1:
        fail(failures, "first-public-issues.json schema_version must be 1")

    gates = manifest.get("publication_gate")
    if not isinstance(gates, list):
        fail(failures, "publication_gate must be a list")
    else:
        gate_set = {gate for gate in gates if isinstance(gate, str)}
        missing_gates = sorted(REQUIRED_PUBLICATION_GATES - gate_set)
        if missing_gates:
            fail(failures, f"publication_gate missing required values: {', '.join(missing_gates)}")

    issues = manifest.get("issues")
    if not isinstance(issues, list) or not issues:
        fail(failures, "issues must be a non-empty list")
    else:
        seen_ids: set[str] = set()
        for index, issue in enumerate(issues, 1):
            validate_issue(issue, index, labels, seen_ids, failures)

    if failures:
        print("First public issue manifest check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("First public issue manifest check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
