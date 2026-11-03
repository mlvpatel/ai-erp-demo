#!/usr/bin/env python3
"""Validate operations, recovery, and incident-response guardrails."""

from __future__ import annotations

import re
from typing import Any

from _gate import REPO_ROOT, doc_phrase_entries, load_json, read_text, rel, report, string_list


MANIFEST_PATH = REPO_ROOT / "config" / "operations-readiness.json"
GITIGNORE = REPO_ROOT / ".gitignore"
GITATTRIBUTES = REPO_ROOT / ".gitattributes"
PUBLICATION_SOURCE_SCRIPT = REPO_ROOT / "scripts" / "check-publication-source.sh"


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    for field in (
        "local_artifact_patterns",
        "local_ignore_patterns",
        "required_doc_phrases",
    ):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            failures.append(f"{field} must be a non-empty list")


def validate_local_artifacts(manifest: dict[str, Any], failures: list[str]) -> None:
    """local_artifact_patterns must be in .gitignore, export-ignored, and excluded by the
    publication-source find; local_ignore_patterns only need the first two. A `!name`
    entry re-includes a file, so .gitattributes must mark it `name -export-ignore`."""
    shared = string_list(manifest.get("local_artifact_patterns"), "local_artifact_patterns", failures)
    ignore_only = string_list(manifest.get("local_ignore_patterns"), "local_ignore_patterns", failures)
    gitignore_text = read_text(GITIGNORE, failures)
    gitignore = {line.strip() for line in gitignore_text.splitlines() if line.strip() and not line.strip().startswith("#")}
    gitattributes = read_text(GITATTRIBUTES, failures)
    source_script = read_text(PUBLICATION_SOURCE_SCRIPT, failures)
    for pattern in shared + ignore_only:
        if pattern not in gitignore:
            failures.append(f".gitignore missing local/recovery artifact pattern: {pattern}")
        attribute = f"{re.escape(pattern[1:])}\\s+-export-ignore" if pattern.startswith("!") else f"{re.escape(pattern)}\\s+export-ignore"
        if not re.search(rf"^{attribute}(?:\s|$)", gitattributes, flags=re.MULTILINE):
            failures.append(f".gitattributes missing export rule for local/recovery artifact pattern: {pattern}")
    for pattern in shared:
        clause = f"-name '{pattern}'" if "*" in pattern else f"-path './{pattern.rstrip('/')}'"
        if clause not in source_script:
            failures.append(f"{rel(PUBLICATION_SOURCE_SCRIPT)} missing publication-source exclusion: {clause}")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_local_artifacts(manifest, failures)
        doc_phrase_entries(manifest, "operations-readiness", failures)

    return report("Operations readiness check", failures)


if __name__ == "__main__":
    raise SystemExit(main())
