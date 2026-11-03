#!/usr/bin/env python3
"""Validate that GitHub Actions CI matches the repository quality contract."""

from __future__ import annotations

import re
import sys
from typing import Any

from _gate import REPO_ROOT, contains_snippet, load_json, read_text


CONTRACT_PATH = REPO_ROOT / "config" / "ci-workflow.json"
METADATA_PATH = REPO_ROOT / ".github" / "repository-metadata.json"

JOB_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


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
        failures.append("repository metadata branch_protection must be an object")
        return set()
    checks = branch_protection.get("required_status_checks")
    if not isinstance(checks, list) or not checks:
        failures.append("repository metadata required_status_checks must be a non-empty list")
        return set()
    result = set()
    for check in checks:
        if not isinstance(check, str) or not check.strip():
            failures.append("repository metadata required_status_checks must contain non-empty strings")
        else:
            result.add(check)
    return result


def validate_contract_shape(contract: dict[str, Any], failures: list[str]) -> None:
    workflow = contract.get("workflow")
    if not isinstance(workflow, str) or not workflow.strip():
        failures.append("workflow must be a non-empty string")


def validate_workflow(contract: dict[str, Any], metadata: dict[str, Any], failures: list[str]) -> None:
    workflow_value = contract.get("workflow")
    if not isinstance(workflow_value, str):
        return
    workflow_path = REPO_ROOT / workflow_value
    workflow_text = read_text(workflow_path, failures)
    if not workflow_text:
        return

    if "branches: [main]" not in workflow_text:
        failures.append("CI workflow must run on pushes to main")
    if "\n  pull_request:" not in workflow_text:
        failures.append("CI workflow must run on pull_request")
    if not contains_snippet(workflow_text, "permissions: contents: read"):
        failures.append("CI workflow permissions must be contents: read")

    for line_number, line in enumerate(workflow_text.splitlines(), 1):
        action = re.search(r"\buses:\s*([^\s#]+)", line)
        if action and not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", action.group(1)):
            failures.append(f"CI workflow action must be pinned to a full commit SHA at line {line_number}")

    forbidden = contract.get("forbidden_snippets", [])
    if not isinstance(forbidden, list):
        failures.append("forbidden_snippets must be a list")
    else:
        for snippet in forbidden:
            if not isinstance(snippet, str):
                failures.append("forbidden_snippets must contain strings")
            elif snippet in workflow_text:
                failures.append(f"CI workflow contains forbidden snippet: {snippet}")

    jobs = contract.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        failures.append("jobs must be a non-empty list")
        return

    blocks = extract_job_blocks(workflow_text)
    metadata_checks = required_status_checks(metadata, failures)
    contract_job_names: set[str] = set()
    seen_job_ids: set[str] = set()

    for index, job in enumerate(jobs, 1):
        if not isinstance(job, dict):
            failures.append(f"jobs[{index}] must be an object")
            continue
        job_id = job.get("id")
        job_name = job.get("name")
        if not isinstance(job_id, str) or not JOB_ID_PATTERN.match(job_id):
            failures.append(f"jobs[{index}].id must be kebab-case")
            continue
        if job_id in seen_job_ids:
            failures.append(f"{job_id}: duplicate job id")
        seen_job_ids.add(job_id)

        if not isinstance(job_name, str) or not job_name.strip():
            failures.append(f"{job_id}: name must be non-empty")
            continue
        contract_job_names.add(job_name)

        block = blocks.get(job_id)
        if block is None:
            failures.append(f"CI workflow missing job id: {job_id}")
            continue
        if f"name: {job_name}" not in block:
            failures.append(f"{job_id}: workflow job name must be {job_name!r}")
        if "runs-on: ubuntu-latest" not in block and "runs-on: ubuntu-24.04" not in block:
            failures.append(f"{job_id}: job must run on an approved Ubuntu runner")

        snippets = job.get("required_snippets")
        if not isinstance(snippets, list) or not snippets:
            failures.append(f"{job_id}: required_snippets must be a non-empty list")
            continue
        for snippet in snippets:
            if not isinstance(snippet, str) or not snippet.strip():
                failures.append(f"{job_id}: required_snippets must contain non-empty strings")
            elif not contains_snippet(block, snippet):
                failures.append(f"{job_id}: required snippet missing: {snippet}")

    if metadata_checks and contract_job_names != metadata_checks:
        failures.append(
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
