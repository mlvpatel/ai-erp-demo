#!/usr/bin/env python3
"""Validate Dependabot and dependency-update policy consistency."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from _gate import REPO_ROOT, contains_snippet, load_json, load_json_object, read_text, rel, report


MANIFEST_PATH = REPO_ROOT / "config" / "dependency-updates.json"
LABELS_PATH = REPO_ROOT / ".github" / "labels.json"
ENV_EXAMPLE = REPO_ROOT / "development" / ".env.example"
E2E_DIR = REPO_ROOT / "tests" / "e2e"
EXACT_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
IMAGE_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


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

    validate_playwright_versions(manifest, env_text, failures)

    phrases = manifest.get("manual_only_doc_phrases")
    if not isinstance(phrases, list) or not phrases:
        failures.append("manual_only_doc_phrases must be a non-empty list")
    else:
        for phrase in phrases:
            if not isinstance(phrase, str):
                failures.append("manual_only_doc_phrases entries must be strings")
            elif not contains_snippet(policy_text, phrase):
                failures.append(f"dependency update workflow missing phrase: {phrase}")


def validate_playwright_versions(
    manifest: dict[str, Any], env_text: str, failures: list[str], e2e_dir: Path = E2E_DIR
) -> None:
    """Keep @playwright/test, its lockfile entry, and PLAYWRIGHT_IMAGE on the recorded version.

    The browser image only carries browsers for its own Playwright version, so a
    package bump without an image bump fails at runtime with a missing executable.
    The image reference is a bare digest, so playwright_image records its version.
    """
    record = manifest.get("playwright_image")
    version = record.get("version") if isinstance(record, dict) else None
    digest = record.get("digest") if isinstance(record, dict) else None
    if not isinstance(version, str) or not EXACT_VERSION.fullmatch(version):
        failures.append("playwright_image.version must be an exact X.Y.Z version")
        return
    if not isinstance(digest, str) or not IMAGE_DIGEST.fullmatch(digest):
        failures.append("playwright_image.digest must be sha256:<64 hex>")
        return

    image = re.search(r"^PLAYWRIGHT_IMAGE=([^\n]+)$", env_text, flags=re.MULTILINE)
    if not image or not image.group(1).endswith(f"@{digest}"):
        failures.append(
            "development/.env.example PLAYWRIGHT_IMAGE digest differs from playwright_image.digest "
            f"(Playwright {version}); update both in the same PR"
        )

    package_path = e2e_dir / "package.json"
    lock_path = e2e_dir / "package-lock.json"
    package = load_json_object(package_path, failures)
    lock = load_json_object(lock_path, failures)
    if package is None or lock is None:
        return
    dev_dependencies = package.get("devDependencies")
    pinned = dev_dependencies.get("@playwright/test") if isinstance(dev_dependencies, dict) else None
    if pinned != version:
        failures.append(
            f"{rel(package_path)} pins @playwright/test {pinned!r}, but PLAYWRIGHT_IMAGE is Playwright {version}"
        )
    packages = lock.get("packages")
    entry = packages.get("node_modules/@playwright/test") if isinstance(packages, dict) else None
    locked = entry.get("version") if isinstance(entry, dict) else None
    if locked != version:
        failures.append(
            f"{rel(lock_path)} resolves @playwright/test {locked!r}, but PLAYWRIGHT_IMAGE is Playwright {version}"
        )


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)
    if manifest:
        validate_manifest_shape(manifest, failures)
        validate_dependabot(manifest, failures)
        validate_manual_pins_and_docs(manifest, failures)

    return report("Dependency update policy check", failures)


if __name__ == "__main__":
    raise SystemExit(main())
