#!/usr/bin/env python3
"""Validate Dependabot and dependency-update policy consistency."""

from __future__ import annotations

import re
import sys
from typing import Any

from _gate import REPO_ROOT, contains_snippet, load_json, read_text


MANIFEST_PATH = REPO_ROOT / "config" / "dependency-updates.json"
LABELS_PATH = REPO_ROOT / ".github" / "labels.json"
ENV_EXAMPLE = REPO_ROOT / "development" / ".env.example"


def label_names(failures: list[str]) -> set[str]:
    labels_manifest = load_json(LABELS_PATH, failures)
    labels = labels_manifest.get("labels", [])
    if not isinstance(labels, list):
        failures.append(".github/labels.json labels must be a list")
        return set()
    names: set[str] = set()
    for index, label in enumerate(labels, 1):
        if not isinstance(label, dict) or not isinstance(label.get("name"), str):
            failures.append(f".github/labels.json labels[{index}] must contain a name")
            continue
        names.add(label["name"])
    return names


def parse_dependabot_updates(text: str) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_labels = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("- package-ecosystem:"):
            if current is not None:
                updates.append(current)
            current = {
                "package_ecosystem": stripped.split(":", 1)[1].strip(),
                "labels": [],
            }
            in_labels = False
            continue
        if current is None:
            continue

        if stripped.startswith("directory:"):
            current["directory"] = stripped.split(":", 1)[1].strip()
            in_labels = False
        elif stripped.startswith("interval:"):
            current["interval"] = stripped.split(":", 1)[1].strip()
            in_labels = False
        elif stripped.startswith("open-pull-requests-limit:"):
            value = stripped.split(":", 1)[1].strip()
            try:
                current["open_pull_requests_limit"] = int(value)
            except ValueError:
                current["open_pull_requests_limit"] = value
            in_labels = False
        elif stripped.startswith("labels:"):
            in_labels = True
        elif in_labels and stripped.startswith("- "):
            current["labels"].append(stripped[2:].strip())
        elif stripped and not raw_line.startswith("      "):
            in_labels = False

    if current is not None:
        updates.append(current)
    return updates


def update_key(update: dict[str, Any]) -> tuple[str, str]:
    return (str(update.get("package_ecosystem")), str(update.get("directory")))


def validate_manifest_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    if manifest.get("dependabot_file") != ".github/dependabot.yml":
        failures.append("dependabot_file must be .github/dependabot.yml")
    if manifest.get("policy_doc") != "docs/workflows/dependency-updates.md":
        failures.append("policy_doc must be docs/workflows/dependency-updates.md")

    entries = manifest.get("required_update_entries")
    if not isinstance(entries, list) or not entries:
        failures.append("required_update_entries must be a non-empty list")
        return
    seen: set[tuple[str, str]] = set()
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            failures.append(f"required_update_entries[{index}] must be an object")
            continue
        for field in ("package_ecosystem", "directory", "interval", "labels", "open_pull_requests_limit"):
            if field not in entry:
                failures.append(f"required_update_entries[{index}] missing {field}")
        key = update_key(entry)
        if key in seen:
            failures.append(f"duplicate dependency update entry for {key}")
        seen.add(key)
        if not isinstance(entry.get("labels"), list) or not entry["labels"]:
            failures.append(f"required_update_entries[{index}].labels must be non-empty")


def validate_dependabot(manifest: dict[str, Any], failures: list[str]) -> None:
    dependabot_file = manifest.get("dependabot_file")
    if not isinstance(dependabot_file, str):
        return
    dependabot_text = read_text(REPO_ROOT / dependabot_file, failures)
    updates = parse_dependabot_updates(dependabot_text)
    actual_by_key = {update_key(update): update for update in updates}

    required_entries = manifest.get("required_update_entries", [])
    expected_by_key = {
        update_key(entry): entry for entry in required_entries if isinstance(entry, dict)
    }

    missing = sorted(set(expected_by_key) - set(actual_by_key))
    extra = sorted(set(actual_by_key) - set(expected_by_key))
    if missing:
        failures.append("Dependabot missing required update entries: " + ", ".join(map(str, missing)))
    if extra:
        failures.append("Dependabot has unmanifested update entries: " + ", ".join(map(str, extra)))

    labels = label_names(failures)
    for key, expected in sorted(expected_by_key.items()):
        actual = actual_by_key.get(key)
        if actual is None:
            continue
        if actual.get("interval") != expected.get("interval"):
            failures.append(f"{key}: interval mismatch")
        if actual.get("open_pull_requests_limit") != expected.get("open_pull_requests_limit"):
            failures.append(f"{key}: open-pull-requests-limit mismatch")
        if actual.get("labels") != expected.get("labels"):
            failures.append(f"{key}: labels mismatch expected={expected.get('labels')} actual={actual.get('labels')}")
        for label in actual.get("labels", []):
            if label not in labels:
                failures.append(f"{key}: Dependabot label is missing from .github/labels.json: {label}")

    forbidden_dirs = set(manifest.get("forbidden_dependabot_directories", []))
    root_allowed = set(manifest.get("root_directory_allowed_ecosystems", []))
    for update in updates:
        directory = update.get("directory")
        ecosystem = update.get("package_ecosystem")
        if directory in forbidden_dirs and ecosystem not in root_allowed:
            failures.append(f"Dependabot must not manage {ecosystem} updates in forbidden directory {directory}")


def validate_manual_pins_and_docs(manifest: dict[str, Any], failures: list[str]) -> None:
    env_text = read_text(ENV_EXAMPLE, failures)
    policy_doc = manifest.get("policy_doc")
    policy_text = read_text(REPO_ROOT / policy_doc, failures) if isinstance(policy_doc, str) else ""

    pins = manifest.get("manual_only_env_pins")
    if not isinstance(pins, list) or not pins:
        failures.append("manual_only_env_pins must be a non-empty list")
    else:
        for pin in pins:
            if not isinstance(pin, str):
                failures.append("manual_only_env_pins entries must be strings")
                continue
            if not re.search(rf"^{re.escape(pin)}=", env_text, flags=re.MULTILINE):
                failures.append(f"development/.env.example missing manual-only pin {pin}")
            if pin not in policy_text:
                failures.append(f"dependency update workflow must mention manual-only pin {pin}")

    for image_pin in ("MARIADB_IMAGE", "REDIS_IMAGE", "FRAPPE_BENCH_IMAGE"):
        match = re.search(rf"^{image_pin}=([^\n]+)$", env_text, flags=re.MULTILINE)
        if not match or "@sha256:" not in match.group(1):
            failures.append(f"{image_pin} must stay digest-pinned")

    for commit_pin in ("FRAPPE_COMMIT", "ERPNEXT_COMMIT"):
        if not re.search(rf"^{commit_pin}=[0-9a-f]{{40}}$", env_text, flags=re.MULTILINE):
            failures.append(f"{commit_pin} must stay pinned to a full commit")

    phrases = manifest.get("manual_only_doc_phrases")
    if not isinstance(phrases, list) or not phrases:
        failures.append("manual_only_doc_phrases must be a non-empty list")
    else:
        for phrase in phrases:
            if not isinstance(phrase, str):
                failures.append("manual_only_doc_phrases entries must be strings")
            elif not contains_snippet(policy_text, phrase):
                failures.append(f"dependency update workflow missing phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)
    if manifest:
        validate_manifest_shape(manifest, failures)
        validate_dependabot(manifest, failures)
        validate_manual_pins_and_docs(manifest, failures)

    if failures:
        print("Dependency update policy check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Dependency update policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
