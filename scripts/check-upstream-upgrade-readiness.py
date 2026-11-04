#!/usr/bin/env python3
"""Validate upstream Frappe/ERPNext upgrade readiness guardrails."""

from __future__ import annotations

import re
from typing import Any

from _gate import (
    REPO_ROOT,
    contains_snippet,
    doc_phrase_entries,
    load_json,
    read_text,
    report,
    required_path,
    string_list,
)


MANIFEST_PATH = REPO_ROOT / "config" / "upstream-upgrade-readiness.json"


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
    for image_pin in ("MARIADB_IMAGE", "REDIS_IMAGE", "FRAPPE_BENCH_IMAGE", "PLAYWRIGHT_IMAGE"):
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


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_env_pins(manifest, failures)
        validate_bootstrap(manifest, failures)
        validate_workflow_commands(manifest, failures)
        doc_phrase_entries(manifest, "upstream-upgrade", failures)

    return report("Upstream upgrade readiness check", failures)


if __name__ == "__main__":
    raise SystemExit(main())
