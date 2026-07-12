#!/usr/bin/env python3
"""Validate that GitHub Actions CI matches the repository quality contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "config" / "ci-workflow.json"
METADATA_PATH = REPO_ROOT / ".github" / "repository-metadata.json"

JOB_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


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


def text(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(failures, f"missing file: {rel(path)}")
        return ""


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def contains_snippet(haystack: str, needle: str) -> bool:
    return normalize_space(needle) in normalize_space(haystack)


def extract_job_blocks(workflow_text: str) -> dict[str, str]:
    lines = workflow_text.splitlines()
    blocks: dict[str, list[str]] = {}
    current_job: str | None = None

    in_jobs = False
    for line in lines:
        if line == "jobs:":
            in_jobs = True
            current_job = None
            continue
        if not in_jobs:
            continue

        match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if match:
            current_job = match.group(1)
            blocks[current_job] = [line]
            continue

        if current_job is not None:
            blocks[current_job].append(line)

    return {job_id: "\n".join(block) for job_id, block in blocks.items()}


def required_status_checks(metadata: dict[str, Any], failures: list[str]) -> set[str]:
    branch_protection = metadata.get("branch_protection")
    if not isinstance(branch_protection, dict):
        fail(failures, "repository metadata branch_protection must be an object")
        return set()
    checks = branch_protection.get("required_status_checks")
    if not isinstance(checks, list) or not checks:
        fail(failures, "repository metadata required_status_checks must be a non-empty list")
        return set()
    result = set()
    for check in checks:
        if not isinstance(check, str) or not check.strip():
            fail(failures, "repository metadata required_status_checks must contain non-empty strings")
        else:
            result.add(check)
    return result


def validate_contract_shape(contract: dict[str, Any], failures: list[str]) -> None:
    if contract.get("schema_version") != 1:
        fail(failures, "ci-workflow.json schema_version must be 1")
    workflow = contract.get("workflow")
    if not isinstance(workflow, str) or not workflow.strip():
        fail(failures, "workflow must be a non-empty string")

    triggers = contract.get("required_triggers")
    if not isinstance(triggers, dict):
        fail(failures, "required_triggers must be an object")
    else:
        if triggers.get("push_branch") != "main":
            fail(failures, "required_triggers.push_branch must be main")
        if triggers.get("pull_request") is not True:
            fail(failures, "required_triggers.pull_request must be true")

    permissions = contract.get("required_permissions")
    if not isinstance(permissions, dict) or permissions.get("contents") != "read":
        fail(failures, "required_permissions.contents must be read")


def validate_workflow(contract: dict[str, Any], metadata: dict[str, Any], failures: list[str]) -> None:
    workflow_value = contract.get("workflow")
    if not isinstance(workflow_value, str):
        return
    workflow_path = REPO_ROOT / workflow_value
    workflow_text = text(workflow_path, failures)
    if not workflow_text:
        return

    if "branches: [main]" not in workflow_text:
        fail(failures, "CI workflow must run on pushes to main")
    if "\n  pull_request:" not in workflow_text:
        fail(failures, "CI workflow must run on pull_request")
    if not contains_snippet(workflow_text, "permissions: contents: read"):
        fail(failures, "CI workflow permissions must be contents: read")

    forbidden = contract.get("forbidden_snippets", [])
    if not isinstance(forbidden, list):
        fail(failures, "forbidden_snippets must be a list")
    else:
        for snippet in forbidden:
            if not isinstance(snippet, str):
                fail(failures, "forbidden_snippets must contain strings")
            elif snippet in workflow_text:
                fail(failures, f"CI workflow contains forbidden snippet: {snippet}")

    jobs = contract.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        fail(failures, "jobs must be a non-empty list")
        return

    blocks = extract_job_blocks(workflow_text)
    metadata_checks = required_status_checks(metadata, failures)
    contract_job_names: set[str] = set()
    seen_job_ids: set[str] = set()

    for index, job in enumerate(jobs, 1):
        if not isinstance(job, dict):
            fail(failures, f"jobs[{index}] must be an object")
            continue
        job_id = job.get("id")
        job_name = job.get("name")
        if not isinstance(job_id, str) or not JOB_ID_PATTERN.match(job_id):
            fail(failures, f"jobs[{index}].id must be kebab-case")
            continue
        if job_id in seen_job_ids:
            fail(failures, f"{job_id}: duplicate job id")
        seen_job_ids.add(job_id)

        if not isinstance(job_name, str) or not job_name.strip():
            fail(failures, f"{job_id}: name must be non-empty")
            continue
        contract_job_names.add(job_name)

        block = blocks.get(job_id)
        if block is None:
            fail(failures, f"CI workflow missing job id: {job_id}")
            continue
        if f"name: {job_name}" not in block:
            fail(failures, f"{job_id}: workflow job name must be {job_name!r}")
        if "runs-on: ubuntu-latest" not in block:
            fail(failures, f"{job_id}: job must run on ubuntu-latest")

        snippets = job.get("required_snippets")
        if not isinstance(snippets, list) or not snippets:
            fail(failures, f"{job_id}: required_snippets must be a non-empty list")
            continue
        for snippet in snippets:
            if not isinstance(snippet, str) or not snippet.strip():
                fail(failures, f"{job_id}: required_snippets must contain non-empty strings")
            elif not contains_snippet(block, snippet):
                fail(failures, f"{job_id}: required snippet missing: {snippet}")

    if metadata_checks and contract_job_names != metadata_checks:
        fail(
            failures,
            "CI contract job names must exactly match repository metadata required_status_checks: "
            f"contract={sorted(contract_job_names)} metadata={sorted(metadata_checks)}",
        )


def main() -> int:
    failures: list[str] = []
    contract = load_json(CONTRACT_PATH, failures)
    metadata = load_json(METADATA_PATH, failures)

    if contract:
        validate_contract_shape(contract, failures)
    if contract and metadata:
        validate_workflow(contract, metadata, failures)

    if failures:
        print("CI workflow check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("CI workflow check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
