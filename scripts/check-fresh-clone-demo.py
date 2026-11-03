#!/usr/bin/env python3
"""Validate fresh-clone demo runbook consistency without starting Docker."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from _gate import REPO_ROOT, contains_snippet, dev_commands, load_json, read_text


MANIFEST_PATH = REPO_ROOT / "config" / "fresh-clone-demo.json"
DEV_HELPER = REPO_ROOT / "scripts" / "dev.sh"
ENV_EXAMPLE = REPO_ROOT / "development" / ".env.example"
COMPOSE_FILE = REPO_ROOT / "infra" / "compose" / "docker-compose.dev.yml"

ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_manifest_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    if manifest.get("status") != "runbook-consistency-check":
        failures.append("fresh-clone-demo.json status must be runbook-consistency-check")

    runbooks = manifest.get("runbooks")
    if not isinstance(runbooks, list) or not runbooks:
        failures.append("runbooks must be a non-empty list")
    else:
        for runbook in runbooks:
            if not isinstance(runbook, str) or not (REPO_ROOT / runbook).is_file():
                failures.append(f"runbook missing or invalid: {runbook!r}")

    required_files = manifest.get("required_files")
    if not isinstance(required_files, list) or not required_files:
        failures.append("required_files must be a non-empty list")
    else:
        for required in required_files:
            if not isinstance(required, str) or not (REPO_ROOT / required).is_file():
                failures.append(f"required fresh-clone file missing: {required!r}")


def validate_env_requirements(manifest: dict[str, Any], failures: list[str]) -> None:
    env_text = read_text(ENV_EXAMPLE, failures)
    requirements = manifest.get("tracked_env_requirements")
    if not isinstance(requirements, list) or not requirements:
        failures.append("tracked_env_requirements must be a non-empty list")
        return

    for requirement in requirements:
        if not isinstance(requirement, str) or not requirement.strip():
            failures.append("tracked_env_requirements entries must be non-empty strings")
            continue
        if "=" in requirement:
            if requirement not in env_text:
                failures.append(f"development/.env.example missing exact setting: {requirement}")
        elif not re.search(rf"^{re.escape(requirement)}=", env_text, flags=re.MULTILINE):
            failures.append(f"development/.env.example missing variable: {requirement}")

    for variable in ("FRAPPE_COMMIT", "ERPNEXT_COMMIT"):
        match = re.search(rf"^{variable}=([0-9a-f]{{40}})$", env_text, flags=re.MULTILINE)
        if not match:
            failures.append(f"{variable} must be pinned to a full commit hash in development/.env.example")

    for variable in ("FRAPPE_BENCH_IMAGE", "MARIADB_IMAGE", "REDIS_IMAGE"):
        match = re.search(rf"^{variable}=([^\n]+)$", env_text, flags=re.MULTILINE)
        if not match or "@sha256:" not in match.group(1):
            failures.append(f"{variable} must use an image digest in development/.env.example")


def validate_compose_services(manifest: dict[str, Any], failures: list[str]) -> None:
    compose_text = read_text(COMPOSE_FILE, failures)
    services = manifest.get("compose_services")
    if not isinstance(services, list) or not services:
        failures.append("compose_services must be a non-empty list")
        return

    for service in services:
        if not isinstance(service, str) or not service.strip():
            failures.append("compose_services entries must be non-empty strings")
            continue
        if f"  {service}:" not in compose_text:
            failures.append(f"Compose service missing: {service}")

    for required in (
        "AI_CONTROL_PLANE_SHARED_SECRET",
        "AI_ERP_PROVIDER",
        "http://ai-control-plane:8090",
        "../../:/workspace:cached",
    ):
        if required not in compose_text:
            failures.append(f"Compose file missing required demo boundary: {required}")


def validate_steps(manifest: dict[str, Any], failures: list[str]) -> None:
    dev_text = read_text(DEV_HELPER, failures)
    commands = dev_commands(dev_text)
    steps = manifest.get("steps")
    if not isinstance(steps, list) or not steps:
        failures.append("steps must be a non-empty list")
        return

    seen_ids: set[str] = set()
    for index, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            failures.append(f"steps[{index}] must be an object")
            continue

        step_id = step.get("id")
        if not isinstance(step_id, str) or not ID_PATTERN.match(step_id):
            failures.append(f"steps[{index}].id must be kebab-case")
            step_id = f"steps[{index}]"
        elif step_id in seen_ids:
            failures.append(f"{step_id}: duplicate step id")
        else:
            seen_ids.add(step_id)

        command = step.get("command")
        dev_command = step.get("dev_command")
        if bool(command) == bool(dev_command):
            failures.append(f"{step_id}: provide exactly one of command or dev_command")
            continue

        expected_text = command if isinstance(command, str) else f"scripts/dev.sh {dev_command}"
        if dev_command:
            if not isinstance(dev_command, str) or dev_command not in commands:
                failures.append(f"{step_id}: dev_command is not documented/implemented by scripts/dev.sh: {dev_command}")
            if f"{dev_command})" not in dev_text:
                failures.append(f"{step_id}: scripts/dev.sh missing case branch for {dev_command}")

        docs = step.get("docs")
        if not isinstance(docs, list) or not docs:
            failures.append(f"{step_id}: docs must be a non-empty list")
            continue
        for doc in docs:
            if not isinstance(doc, str):
                failures.append(f"{step_id}: docs entries must be strings")
                continue
            doc_text = read_text(REPO_ROOT / doc, failures)
            if expected_text and not contains_snippet(doc_text, expected_text):
                failures.append(f"{step_id}: {doc} must mention {expected_text!r}")


def validate_safety_phrases(manifest: dict[str, Any], failures: list[str]) -> None:
    runbook_text = "\n".join(
        read_text(REPO_ROOT / path, failures)
        for path in manifest.get("runbooks", [])
        if isinstance(path, str)
    )
    dev_text = read_text(DEV_HELPER, failures)
    combined = runbook_text + "\n" + dev_text

    phrases = manifest.get("required_safety_phrases")
    if not isinstance(phrases, list) or not phrases:
        failures.append("required_safety_phrases must be a non-empty list")
        return
    for phrase in phrases:
        if not isinstance(phrase, str) or not phrase.strip():
            failures.append("required_safety_phrases entries must be non-empty strings")
        elif not contains_snippet(combined, phrase):
            failures.append(f"fresh-clone safety phrase missing: {phrase}")


def demo_info_output(env_file: Path, failures: list[str]) -> str:
    env = os.environ.copy()
    env["AI_ERP_ENV_FILE"] = str(env_file)
    try:
        result = subprocess.run(
            [str(DEV_HELPER), "demo-info"],
            cwd=REPO_ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError as exc:
        failures.append(f"could not execute scripts/dev.sh demo-info: {exc}")
        return ""
    except subprocess.TimeoutExpired:
        failures.append("scripts/dev.sh demo-info timed out")
        return ""

    output = result.stdout + result.stderr
    if result.returncode != 0:
        failures.append(f"scripts/dev.sh demo-info exited with {result.returncode}: {output.strip()}")
    return output


def validate_demo_info_output(manifest: dict[str, Any], failures: list[str]) -> None:
    contract = manifest.get("demo_info_output_contract")
    if not isinstance(contract, dict):
        failures.append("demo_info_output_contract must be an object")
        return

    existing_env = contract.get("existing_env_file")
    if not isinstance(existing_env, str) or not existing_env.strip():
        failures.append("demo_info_output_contract.existing_env_file must be a non-empty string")
        return
    existing_env_path = REPO_ROOT / existing_env
    if not existing_env_path.is_file():
        failures.append(f"demo-info existing env file is missing: {existing_env}")
        return

    existing_output = demo_info_output(existing_env_path, failures)
    for phrase in contract.get("required_phrases", []):
        if not isinstance(phrase, str) or not phrase.strip():
            failures.append("demo_info_output_contract.required_phrases entries must be non-empty strings")
        elif not contains_snippet(existing_output, phrase):
            failures.append(f"demo-info output missing required phrase: {phrase}")

    custom_env_path = Path("./.pycache/ai-erp-demo-info-output-safety-does-not-exist.env")
    custom_output = demo_info_output(custom_env_path, failures)
    for phrase in contract.get("custom_env_required_phrases", []):
        if not isinstance(phrase, str) or not phrase.strip():
            failures.append("demo_info_output_contract.custom_env_required_phrases entries must be non-empty strings")
        elif not contains_snippet(custom_output, phrase):
            failures.append(f"demo-info custom-env output missing required phrase: {phrase}")

    combined_output = existing_output + "\n" + custom_output
    dynamic_forbidden = [
        str(REPO_ROOT),
        str(existing_env_path),
        str(custom_env_path),
    ]
    for forbidden in dynamic_forbidden:
        if forbidden and forbidden in combined_output:
            failures.append(f"demo-info output leaked local path: {forbidden}")

    for forbidden in contract.get("forbidden_substrings", []):
        if not isinstance(forbidden, str) or not forbidden:
            failures.append("demo_info_output_contract.forbidden_substrings entries must be non-empty strings")
        elif forbidden in combined_output:
            failures.append(f"demo-info output leaked forbidden text: {forbidden}")

    env_assignment_re = re.compile(r"(?m)^[A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|KEY)[A-Z0-9_]*=")
    if env_assignment_re.search(combined_output):
        failures.append("demo-info output leaked a raw secret-like environment assignment")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_manifest_shape(manifest, failures)
        validate_env_requirements(manifest, failures)
        validate_compose_services(manifest, failures)
        validate_steps(manifest, failures)
        validate_safety_phrases(manifest, failures)
        validate_demo_info_output(manifest, failures)

    if failures:
        print("Fresh-clone demo check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Fresh-clone demo check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
