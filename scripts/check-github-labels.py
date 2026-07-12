#!/usr/bin/env python3
"""Validate GitHub labels referenced by templates and triage docs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
LABELS_FILE = REPO_ROOT / ".github" / "labels.json"
ISSUE_TEMPLATE_DIR = REPO_ROOT / ".github" / "ISSUE_TEMPLATE"
DOCS_WITH_LABEL_REFERENCES = [
    REPO_ROOT / "BACKLOG.md",
    REPO_ROOT / "docs" / "workflows" / "issue-triage.md",
]

LABEL_ARRAY_PATTERN = re.compile(r"^labels:\s*\[(.*)\]\s*$", re.MULTILINE)
QUOTED_VALUE_PATTERN = re.compile(r'"([^"]+)"|\'([^\']+)\'')
BACKTICK_VALUE_PATTERN = re.compile(r"`([^`]+)`")
HEX_COLOR_PATTERN = re.compile(r"^[0-9A-Fa-f]{6}$")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def load_manifest(failures: list[str]) -> list[dict[str, Any]]:
    try:
        manifest = json.loads(LABELS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(failures, f"missing label manifest: {rel(LABELS_FILE)}")
        return []
    except json.JSONDecodeError as exc:
        fail(failures, f"invalid JSON in {rel(LABELS_FILE)}: {exc}")
        return []

    if manifest.get("schema_version") != 1:
        fail(failures, "labels.json schema_version must be 1")

    labels = manifest.get("labels")
    if not isinstance(labels, list) or not labels:
        fail(failures, "labels.json must contain a non-empty labels list")
        return []
    return labels


def validate_manifest_labels(failures: list[str], labels: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()

    for index, label in enumerate(labels, 1):
        if not isinstance(label, dict):
            fail(failures, f"labels[{index}] must be an object")
            continue

        name = label.get("name")
        color = label.get("color")
        description = label.get("description")

        if not isinstance(name, str) or not name.strip():
            fail(failures, f"labels[{index}].name must be a non-empty string")
            continue
        if name != name.strip() or "  " in name:
            fail(failures, f"{name!r}: label name has suspicious whitespace")
        if name in names:
            fail(failures, f"{name}: duplicate label name")
        names.add(name)

        if not isinstance(color, str) or not HEX_COLOR_PATTERN.match(color):
            fail(failures, f"{name}: color must be a six-character hex value")
        if not isinstance(description, str) or not description.strip():
            fail(failures, f"{name}: description must be non-empty")
        elif len(description) > 100:
            fail(failures, f"{name}: description should be 100 characters or less")

    return names


def parse_template_labels(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    match = LABEL_ARRAY_PATTERN.search(text)
    if not match:
        return set()
    values = set()
    for quoted in QUOTED_VALUE_PATTERN.finditer(match.group(1)):
        value = quoted.group(1) or quoted.group(2)
        if value:
            values.add(value)
    return values


def label_like(value: str) -> bool:
    if "/" in value or "." in value:
        return False
    if value.endswith(".md") or value.endswith(".sh"):
        return False
    return bool(re.fullmatch(r"[a-z][a-z0-9 -]*", value))


def referenced_labels() -> dict[str, set[str]]:
    references: dict[str, set[str]] = {}

    for template in sorted(ISSUE_TEMPLATE_DIR.glob("*.md")):
        labels = parse_template_labels(template)
        if labels:
            references[rel(template)] = labels

    for path in DOCS_WITH_LABEL_REFERENCES:
        if not path.exists():
            continue
        labels = {
            value
            for value in BACKTICK_VALUE_PATTERN.findall(path.read_text(encoding="utf-8"))
            if label_like(value)
        }
        if labels:
            references[rel(path)] = labels

    return references


def main() -> int:
    failures: list[str] = []
    labels = load_manifest(failures)
    manifest_names = validate_manifest_labels(failures, labels)
    references = referenced_labels()

    for source, labels_in_source in sorted(references.items()):
        missing = sorted(labels_in_source - manifest_names)
        if missing:
            fail(failures, f"{source}: missing labels in manifest: {', '.join(missing)}")

    if "blocked-license" not in manifest_names:
        fail(failures, "blocked-license label is required while ADR-0005 is unresolved")
    if "erp-safety" not in manifest_names or "ai-safety" not in manifest_names:
        fail(failures, "erp-safety and ai-safety labels are required")
    if "good first issue" not in manifest_names:
        fail(failures, "good first issue label is required for contributor onboarding")

    if failures:
        print("GitHub label check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("GitHub label check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
