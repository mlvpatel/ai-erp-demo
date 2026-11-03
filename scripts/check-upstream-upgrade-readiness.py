#!/usr/bin/env python3
"""Validate upstream Frappe/ERPNext upgrade readiness guardrails."""

from __future__ import annotations

import re
import sys
from typing import Any

from _gate import REPO_ROOT, load_json, read_text


MANIFEST_PATH = REPO_ROOT / "config" / "upstream-upgrade-readiness.json"


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def contains_snippet(haystack: str, needle: str) -> bool:
    return normalize_space(needle) in normalize_space(haystack)


def string_list(value: Any, field: str, failures: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        failures.append(f"{field} must be a non-empty list")
        return []
    result: list[str] = []
    for index, item in enumerate(value, 1):
        if not isinstance(item, str) or not item.strip():
            failures.append(f"{field}[{index}] must be a non-empty string")
            continue
        result.append(item)
    return result


def required_path(manifest: dict[str, Any], field: str, failures: list[str]) -> str | None:
    value = manifest.get(field)
    if not isinstance(value, str) or not value.strip():
        failures.append(f"{field} must be a non-empty string")
        return None
    if not (REPO_ROOT / value).is_file():
        failures.append(f"{field} path is missing: {value}")
    return value


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    for field in (
        "workflow_doc",
        "env_example",
        "bootstrap_script",
    ):
        required_path(manifest, field, failures)

    for field in (
        "required_env_pins",
        "required_validation_commands",
        "bootstrap_required_snippets",
        "required_doc_phrases",
    ):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            failures.append(f"{field} must be a non-empty list")


def validate_env_pins(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("env_example")
    if not isinstance(path_value, str):
        return
    env_text = read_text(REPO_ROOT / path_value, failures)
    for pin in string_list(manifest.get("required_env_pins"), "required_env_pins", failures):
        if not re.search(rf"^{re.escape(pin)}=", env_text, flags=re.MULTILINE):
            failures.append(f"{path_value} missing pin: {pin}")

    if not re.search(r"^FRAPPE_BRANCH=version-[0-9]+$", env_text, flags=re.MULTILINE):
        failures.append(f"{path_value} must pin FRAPPE_BRANCH to an explicit version branch")
    for commit_pin in ("FRAPPE_COMMIT", "ERPNEXT_COMMIT"):
        if not re.search(rf"^{commit_pin}=[0-9a-f]{{40}}$", env_text, flags=re.MULTILINE):
            failures.append(f"{path_value} {commit_pin} must be a full 40-character commit hash")
    for image_pin in ("MARIADB_IMAGE", "REDIS_IMAGE", "FRAPPE_BENCH_IMAGE"):
        if not re.search(rf"^{image_pin}=\S+@sha256:[0-9a-f]{{64}}$", env_text, flags=re.MULTILINE):
            failures.append(f"{path_value} {image_pin} must be digest-pinned")

    compose_path = "infra/compose/docker-compose.dev.yml"
    for name, body in ((path_value, env_text), (compose_path, read_text(REPO_ROOT / compose_path, failures))):
        if re.search(r":latest|frappe/bench:|mariadb:[0-9]|redis:[0-9]", body):
            failures.append(f"{name}: use digest-pinned images, not tags")


def validate_bootstrap(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("bootstrap_script")
    if not isinstance(path_value, str):
        return
    text = read_text(REPO_ROOT / path_value, failures)
    for snippet in string_list(manifest.get("bootstrap_required_snippets"), "bootstrap_required_snippets", failures):
        if not contains_snippet(text, snippet):
            failures.append(f"{path_value} missing bootstrap safety snippet: {snippet}")


def validate_workflow_commands(manifest: dict[str, Any], failures: list[str]) -> None:
    workflow_path = manifest.get("workflow_doc")
    if not isinstance(workflow_path, str):
        return
    text = read_text(REPO_ROOT / workflow_path, failures)
    for command in string_list(manifest.get("required_validation_commands"), "required_validation_commands", failures):
        if not contains_snippet(text, command):
            failures.append(f"{workflow_path} missing validation command: {command}")


def validate_docs(manifest: dict[str, Any], failures: list[str]) -> None:
    entries = manifest.get("required_doc_phrases")
    if not isinstance(entries, list):
        return
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            failures.append(f"required_doc_phrases[{index}] must be an object")
            continue
        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value:
            failures.append(f"required_doc_phrases[{index}].path must be a non-empty string")
            continue
        text = read_text(REPO_ROOT / path_value, failures)
        for phrase in string_list(entry.get("phrases"), f"required_doc_phrases[{index}].phrases", failures):
            if not contains_snippet(text, phrase):
                failures.append(f"{path_value} missing upstream-upgrade phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_env_pins(manifest, failures)
        validate_bootstrap(manifest, failures)
        validate_workflow_commands(manifest, failures)
        validate_docs(manifest, failures)

    if failures:
        print("Upstream upgrade readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Upstream upgrade readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
