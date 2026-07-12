#!/usr/bin/env python3
"""Validate fresh-clone demo runbook consistency without starting Docker."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "fresh-clone-demo.json"
DEV_HELPER = REPO_ROOT / "scripts" / "dev.sh"
ENV_EXAMPLE = REPO_ROOT / "development" / ".env.example"
COMPOSE_FILE = REPO_ROOT / "infra" / "compose" / "docker-compose.dev.yml"

ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


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


def dev_commands(dev_text: str) -> set[str]:
    commands = set(re.findall(r"^\s{2}([a-z][a-z0-9-]*)\s", dev_text, flags=re.MULTILINE))
    case_labels = set(re.findall(r"^\s{2}([a-z][a-z0-9-]*)\)", dev_text, flags=re.MULTILINE))
    return commands | case_labels


def validate_manifest_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    if manifest.get("schema_version") != 1:
        fail(failures, "fresh-clone-demo.json schema_version must be 1")
    if manifest.get("status") != "runbook-consistency-check":
        fail(failures, "fresh-clone-demo.json status must be runbook-consistency-check")

    runbooks = manifest.get("runbooks")
    if not isinstance(runbooks, list) or not runbooks:
        fail(failures, "runbooks must be a non-empty list")
    else:
        for runbook in runbooks:
            if not isinstance(runbook, str) or not (REPO_ROOT / runbook).is_file():
                fail(failures, f"runbook missing or invalid: {runbook!r}")

    required_files = manifest.get("required_files")
    if not isinstance(required_files, list) or not required_files:
        fail(failures, "required_files must be a non-empty list")
    else:
        for required in required_files:
            if not isinstance(required, str) or not (REPO_ROOT / required).is_file():
                fail(failures, f"required fresh-clone file missing: {required!r}")


def validate_env_requirements(manifest: dict[str, Any], failures: list[str]) -> None:
    env_text = read_text(ENV_EXAMPLE, failures)
    requirements = manifest.get("tracked_env_requirements")
    if not isinstance(requirements, list) or not requirements:
        fail(failures, "tracked_env_requirements must be a non-empty list")
        return

    for requirement in requirements:
        if not isinstance(requirement, str) or not requirement.strip():
            fail(failures, "tracked_env_requirements entries must be non-empty strings")
            continue
        if "=" in requirement:
            if requirement not in env_text:
                fail(failures, f"development/.env.example missing exact setting: {requirement}")
        elif not re.search(rf"^{re.escape(requirement)}=", env_text, flags=re.MULTILINE):
            fail(failures, f"development/.env.example missing variable: {requirement}")

    for variable in ("FRAPPE_COMMIT", "ERPNEXT_COMMIT"):
        match = re.search(rf"^{variable}=([0-9a-f]{{40}})$", env_text, flags=re.MULTILINE)
        if not match:
            fail(failures, f"{variable} must be pinned to a full commit hash in development/.env.example")

    for variable in ("FRAPPE_BENCH_IMAGE", "MARIADB_IMAGE", "REDIS_IMAGE"):
        match = re.search(rf"^{variable}=([^\n]+)$", env_text, flags=re.MULTILINE)
        if not match or "@sha256:" not in match.group(1):
            fail(failures, f"{variable} must use an image digest in development/.env.example")


def validate_compose_services(manifest: dict[str, Any], failures: list[str]) -> None:
    compose_text = read_text(COMPOSE_FILE, failures)
    services = manifest.get("compose_services")
    if not isinstance(services, list) or not services:
        fail(failures, "compose_services must be a non-empty list")
        return

    for service in services:
        if not isinstance(service, str) or not service.strip():
            fail(failures, "compose_services entries must be non-empty strings")
            continue
        if f"  {service}:" not in compose_text:
            fail(failures, f"Compose service missing: {service}")

    for required in (
        "AI_CONTROL_PLANE_SHARED_SECRET",
        "AI_ERP_PROVIDER",
        "http://ai-control-plane:8090",
        "../../:/workspace:cached",
    ):
        if required not in compose_text:
            fail(failures, f"Compose file missing required demo boundary: {required}")


def validate_steps(manifest: dict[str, Any], failures: list[str]) -> None:
    dev_text = read_text(DEV_HELPER, failures)
    commands = dev_commands(dev_text)
    steps = manifest.get("steps")
    if not isinstance(steps, list) or not steps:
        fail(failures, "steps must be a non-empty list")
        return

    seen_ids: set[str] = set()
    for index, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            fail(failures, f"steps[{index}] must be an object")
            continue

        step_id = step.get("id")
        if not isinstance(step_id, str) or not ID_PATTERN.match(step_id):
            fail(failures, f"steps[{index}].id must be kebab-case")
            step_id = f"steps[{index}]"
        elif step_id in seen_ids:
            fail(failures, f"{step_id}: duplicate step id")
        else:
            seen_ids.add(step_id)

        command = step.get("command")
        dev_command = step.get("dev_command")
        if bool(command) == bool(dev_command):
            fail(failures, f"{step_id}: provide exactly one of command or dev_command")
            continue

        expected_text = command if isinstance(command, str) else f"scripts/dev.sh {dev_command}"
        if dev_command:
            if not isinstance(dev_command, str) or dev_command not in commands:
                fail(failures, f"{step_id}: dev_command is not documented/implemented by scripts/dev.sh: {dev_command}")
            if f"{dev_command})" not in dev_text:
                fail(failures, f"{step_id}: scripts/dev.sh missing case branch for {dev_command}")

        docs = step.get("docs")
        if not isinstance(docs, list) or not docs:
            fail(failures, f"{step_id}: docs must be a non-empty list")
            continue
        for doc in docs:
            if not isinstance(doc, str):
                fail(failures, f"{step_id}: docs entries must be strings")
                continue
            doc_text = read_text(REPO_ROOT / doc, failures)
            if expected_text and not contains_snippet(doc_text, expected_text):
                fail(failures, f"{step_id}: {doc} must mention {expected_text!r}")


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
        fail(failures, "required_safety_phrases must be a non-empty list")
        return
    for phrase in phrases:
        if not isinstance(phrase, str) or not phrase.strip():
            fail(failures, "required_safety_phrases entries must be non-empty strings")
        elif not contains_snippet(combined, phrase):
            fail(failures, f"fresh-clone safety phrase missing: {phrase}")


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
        fail(failures, f"could not execute scripts/dev.sh demo-info: {exc}")
        return ""
    except subprocess.TimeoutExpired:
        fail(failures, "scripts/dev.sh demo-info timed out")
        return ""

    output = result.stdout + result.stderr
    if result.returncode != 0:
        fail(failures, f"scripts/dev.sh demo-info exited with {result.returncode}: {output.strip()}")
    return output


def validate_demo_info_output(manifest: dict[str, Any], failures: list[str]) -> None:
    contract = manifest.get("demo_info_output_contract")
    if not isinstance(contract, dict):
        fail(failures, "demo_info_output_contract must be an object")
        return

    existing_env = contract.get("existing_env_file")
    if not isinstance(existing_env, str) or not existing_env.strip():
        fail(failures, "demo_info_output_contract.existing_env_file must be a non-empty string")
        return
    existing_env_path = REPO_ROOT / existing_env
    if not existing_env_path.is_file():
        fail(failures, f"demo-info existing env file is missing: {existing_env}")
        return

    existing_output = demo_info_output(existing_env_path, failures)
    for phrase in contract.get("required_phrases", []):
        if not isinstance(phrase, str) or not phrase.strip():
            fail(failures, "demo_info_output_contract.required_phrases entries must be non-empty strings")
        elif not contains_snippet(existing_output, phrase):
            fail(failures, f"demo-info output missing required phrase: {phrase}")

    custom_env_path = Path("/tmp/ai-erp-demo-info-output-safety-does-not-exist.env")
    custom_output = demo_info_output(custom_env_path, failures)
    for phrase in contract.get("custom_env_required_phrases", []):
        if not isinstance(phrase, str) or not phrase.strip():
            fail(failures, "demo_info_output_contract.custom_env_required_phrases entries must be non-empty strings")
        elif not contains_snippet(custom_output, phrase):
            fail(failures, f"demo-info custom-env output missing required phrase: {phrase}")

    combined_output = existing_output + "\n" + custom_output
    dynamic_forbidden = [
        str(REPO_ROOT),
        str(existing_env_path),
        str(custom_env_path),
    ]
    for forbidden in dynamic_forbidden:
        if forbidden and forbidden in combined_output:
            fail(failures, f"demo-info output leaked local path: {forbidden}")

    for forbidden in contract.get("forbidden_substrings", []):
        if not isinstance(forbidden, str) or not forbidden:
            fail(failures, "demo_info_output_contract.forbidden_substrings entries must be non-empty strings")
        elif forbidden in combined_output:
            fail(failures, f"demo-info output leaked forbidden text: {forbidden}")

    env_assignment_re = re.compile(r"(?m)^[A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|KEY)[A-Z0-9_]*=")
    if env_assignment_re.search(combined_output):
        fail(failures, "demo-info output leaked a raw secret-like environment assignment")


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
