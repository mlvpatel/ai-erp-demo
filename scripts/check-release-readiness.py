#!/usr/bin/env python3
"""Validate release readiness blockers and, optionally, local strict state."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "release-readiness.json"
METADATA_PATH = REPO_ROOT / ".github" / "repository-metadata.json"
TRACEABILITY_PATH = REPO_ROOT / "docs" / "product" / "requirements-traceability.md"
PUBLICATION_RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "github-publication.md"

ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VALID_CATEGORIES = {"owner-decision", "local-state", "external-verification"}
VALID_STATUSES = {"blocked", "prepared", "manual"}
METADATA_PLACEHOLDER_PATTERN = re.compile(r"(\[year\]|\[fullname\]|opensource@ai-erp\.example)")
PUBLISHABLE_SUFFIXES = {".md", ".py", ".toml", ".txt"}


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


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)


def publishable_app_service_files() -> list[Path]:
    roots = [REPO_ROOT / "apps", REPO_ROOT / "services"]
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in PUBLISHABLE_SUFFIXES:
                files.append(path)
    return files


def validate_strict_check(blocker_id: str, check: Any, failures: list[str], strict: bool) -> None:
    if not isinstance(check, dict):
        fail(failures, f"{blocker_id}: strict_checks entries must be objects")
        return

    check_type = check.get("type")
    if check_type == "file_present":
        path_value = check.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            fail(failures, f"{blocker_id}: file_present check needs path")
        elif strict and not (REPO_ROOT / path_value).is_file():
            fail(failures, f"{blocker_id}: required release file is missing: {path_value}")
    elif check_type == "no_metadata_placeholders":
        if strict:
            matches = []
            for path in publishable_app_service_files():
                for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if METADATA_PLACEHOLDER_PATTERN.search(line):
                        matches.append(f"{rel(path)}:{line_no}:{line}")
            if matches:
                fail(
                    failures,
                    blocker_id
                    + ": generated metadata placeholders remain:\n"
                    + "\n".join(matches),
                )
    elif check_type == "local_artifacts_absent":
        if strict:
            result = run(["scripts/local-artifacts.sh", "--count"])
            if result.returncode != 0:
                fail(failures, f"{blocker_id}: local artifact count command failed: {result.stderr.strip()}")
            else:
                count_text = result.stdout.strip()
                try:
                    count = int(count_text)
                except ValueError:
                    fail(failures, f"{blocker_id}: invalid local artifact count: {count_text!r}")
                else:
                    if count != 0:
                        fail(failures, f"{blocker_id}: {count} local generated artifact(s) remain")
    elif check_type == "publication_source_strict":
        if strict:
            result = run(["scripts/check-publication-source.sh", "--strict"])
            if result.returncode != 0:
                detail = (result.stdout + result.stderr).strip()
                fail(failures, f"{blocker_id}: publication source strict check failed:\n{detail}")
    else:
        fail(failures, f"{blocker_id}: unsupported strict check type {check_type!r}")


def validate_blocker(
    blocker: Any,
    index: int,
    metadata_blockers: set[str],
    traceability_text: str,
    runbook_text: str,
    seen_ids: set[str],
    failures: list[str],
    strict: bool,
) -> None:
    if not isinstance(blocker, dict):
        fail(failures, f"blockers[{index}] must be an object")
        return

    blocker_id = blocker.get("id")
    if not isinstance(blocker_id, str) or not ID_PATTERN.match(blocker_id):
        fail(failures, f"blockers[{index}].id must be kebab-case")
        blocker_id = f"blockers[{index}]"
    elif blocker_id in seen_ids:
        fail(failures, f"{blocker_id}: duplicate blocker id")
    else:
        seen_ids.add(blocker_id)

    title = blocker.get("title")
    if not isinstance(title, str) or not title.strip():
        fail(failures, f"{blocker_id}: title must be non-empty")

    category = blocker.get("category")
    if category not in VALID_CATEGORIES:
        fail(failures, f"{blocker_id}: category must be one of {', '.join(sorted(VALID_CATEGORIES))}")

    status = blocker.get("status")
    if status not in VALID_STATUSES:
        fail(failures, f"{blocker_id}: status must be one of {', '.join(sorted(VALID_STATUSES))}")

    evidence_paths = blocker.get("evidence_paths")
    if not isinstance(evidence_paths, list) or not evidence_paths:
        fail(failures, f"{blocker_id}: evidence_paths must be a non-empty list")
    else:
        for evidence in evidence_paths:
            if not isinstance(evidence, str):
                fail(failures, f"{blocker_id}: every evidence path must be a string")
            elif not (REPO_ROOT / evidence).exists():
                fail(failures, f"{blocker_id}: evidence path does not exist: {evidence}")

    metadata_text = blocker.get("github_metadata_text")
    if not isinstance(metadata_text, str) or metadata_text not in metadata_blockers:
        fail(failures, f"{blocker_id}: github_metadata_text is not listed in .github/repository-metadata.json")

    trace_text = blocker.get("traceability_text")
    if not isinstance(trace_text, str) or not contains_snippet(traceability_text, trace_text):
        fail(failures, f"{blocker_id}: traceability_text not found in requirements traceability doc")

    runbook_snippet = blocker.get("runbook_text")
    if not isinstance(runbook_snippet, str) or not contains_snippet(runbook_text, runbook_snippet):
        fail(failures, f"{blocker_id}: runbook_text not found in GitHub publication runbook")

    strict_checks = blocker.get("strict_checks")
    if not isinstance(strict_checks, list):
        fail(failures, f"{blocker_id}: strict_checks must be a list")
    else:
        if category != "external-verification" and not strict_checks:
            fail(failures, f"{blocker_id}: non-external blockers need at least one strict check")
        for check in strict_checks:
            validate_strict_check(blocker_id, check, failures, strict)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="also evaluate local release state; expected to fail until owner/local blockers are resolved",
    )
    args = parser.parse_args()

    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)
    metadata = load_json(METADATA_PATH, failures)
    traceability_text = read_text(TRACEABILITY_PATH, failures)
    runbook_text = read_text(PUBLICATION_RUNBOOK_PATH, failures)

    if manifest.get("schema_version") != 1:
        fail(failures, "release-readiness.json schema_version must be 1")
    if manifest.get("status") != "blocked-until-owner-and-publication-gates-pass":
        fail(failures, "release-readiness.json status must reflect unresolved publication gates")
    if manifest.get("strict_release_command") != "scripts/check-open-source-ready.sh --release":
        fail(failures, "strict_release_command must be scripts/check-open-source-ready.sh --release")

    metadata_blockers_raw = metadata.get("public_release_blockers")
    if not isinstance(metadata_blockers_raw, list):
        fail(failures, ".github/repository-metadata.json public_release_blockers must be a list")
        metadata_blockers: set[str] = set()
    else:
        metadata_blockers = {
            item for item in metadata_blockers_raw if isinstance(item, str)
        }

    blockers = manifest.get("blockers")
    manifest_metadata_texts: set[str] = set()
    if not isinstance(blockers, list) or not blockers:
        fail(failures, "blockers must be a non-empty list")
    else:
        seen_ids: set[str] = set()
        for index, blocker in enumerate(blockers, 1):
            if isinstance(blocker, dict) and isinstance(blocker.get("github_metadata_text"), str):
                manifest_metadata_texts.add(blocker["github_metadata_text"])
            validate_blocker(
                blocker,
                index,
                metadata_blockers,
                traceability_text,
                runbook_text,
                seen_ids,
                failures,
                args.strict,
            )

    missing_from_manifest = sorted(metadata_blockers - manifest_metadata_texts)
    if missing_from_manifest:
        fail(
            failures,
            "GitHub metadata public_release_blockers missing from release manifest: "
            + "; ".join(missing_from_manifest),
        )

    if failures:
        label = "Release readiness strict check failed" if args.strict else "Release readiness manifest check failed"
        print(label + ":", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    if args.strict:
        print("Release readiness strict check passed.")
    else:
        print("Release readiness manifest check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
