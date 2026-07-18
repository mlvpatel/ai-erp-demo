#!/usr/bin/env python3
"""Validate AI workflow registry, lifecycle docs, and implemented workflow proofs."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "config" / "ai-workflow-registry.json"
ALLOWED_STATUSES = {"proposed", "approved_for_implementation", "implemented"}
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
ROUTE_PATTERN = re.compile(r"^(GET|POST|PUT|PATCH|DELETE) /[A-Za-z0-9/_{}.-]+$")


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


def parse_python(path: Path, failures: list[str]) -> ast.Module | None:
    source = read_text(path, failures)
    if not source:
        return None
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        fail(failures, f"invalid Python in {rel(path)}: {exc}")
        return None


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def contains_snippet(haystack: str, needle: str) -> bool:
    return normalize_space(needle) in normalize_space(haystack)


def string_list(value: Any, field: str, failures: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        fail(failures, f"{field} must be a non-empty list")
        return []
    result: list[str] = []
    for index, item in enumerate(value, 1):
        if not isinstance(item, str) or not item.strip():
            fail(failures, f"{field}[{index}] must be a non-empty string")
            continue
        result.append(item)
    return result


def python_has_function(path: Path, function_name: str, failures: list[str]) -> bool:
    module = parse_python(path, failures)
    if module is None:
        return False
    return any(isinstance(node, ast.FunctionDef) and node.name == function_name for node in module.body)


def python_has_class(path: Path, class_name: str, failures: list[str]) -> bool:
    module = parse_python(path, failures)
    if module is None:
        return False
    return any(isinstance(node, ast.ClassDef) and node.name == class_name for node in module.body)


def validate_shape(registry: dict[str, Any], failures: list[str]) -> None:
    if registry.get("schema_version") != 1:
        fail(failures, "ai-workflow-registry.json schema_version must be 1")

    for field in ("lifecycle_doc", "review_checklist", "threat_model"):
        value = registry.get(field)
        if not isinstance(value, str) or not value.strip():
            fail(failures, f"{field} must be a non-empty string")
        elif not (REPO_ROOT / value).is_file():
            fail(failures, f"{field} path is missing: {value}")

    for field in ("required_lifecycle_doc_phrases", "required_review_doc_phrases"):
        string_list(registry.get(field), field, failures)

    workflows = registry.get("workflows")
    if not isinstance(workflows, list) or not workflows:
        fail(failures, "workflows must be a non-empty list")
        return

    seen_ids: set[str] = set()
    for index, workflow in enumerate(workflows, 1):
        if not isinstance(workflow, dict):
            fail(failures, f"workflows[{index}] must be an object")
            continue
        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, str) or not ID_PATTERN.match(workflow_id):
            fail(failures, f"workflows[{index}].id must be snake_case")
        elif workflow_id in seen_ids:
            fail(failures, f"{workflow_id}: duplicate AI workflow id")
        else:
            seen_ids.add(workflow_id)

        status = workflow.get("status")
        if status not in ALLOWED_STATUSES:
            fail(failures, f"{workflow_id}: status must be one of {', '.join(sorted(ALLOWED_STATUSES))}")
        route = workflow.get("route")
        if not isinstance(route, str) or not ROUTE_PATTERN.match(route):
            fail(failures, f"{workflow_id}: route must look like 'POST /path'")
        if not isinstance(workflow.get("proposal_type"), str) or not workflow["proposal_type"].strip():
            fail(failures, f"{workflow_id}: proposal_type must be a non-empty string")

        policy = workflow.get("policy")
        if not isinstance(policy, dict):
            fail(failures, f"{workflow_id}: policy must be an object")
        elif policy.get("decision") != "draft_only" or policy.get("allowed_action") != "none":
            fail(failures, f"{workflow_id}: MVP AI policy must be draft_only/none")

        for field in ("docs", "tests", "proof_commands", "forbidden_direct_actions"):
            string_list(workflow.get(field), f"{workflow_id}.{field}", failures)


def validate_registry_docs(registry: dict[str, Any], failures: list[str]) -> None:
    doc_checks = (
        ("lifecycle_doc", "required_lifecycle_doc_phrases"),
        ("review_checklist", "required_review_doc_phrases"),
    )
    for path_field, phrases_field in doc_checks:
        path_value = registry.get(path_field)
        if not isinstance(path_value, str):
            continue
        text = read_text(REPO_ROOT / path_value, failures)
        for phrase in string_list(registry.get(phrases_field), phrases_field, failures):
            if not contains_snippet(text, phrase):
                fail(failures, f"{path_value}: missing AI workflow registry phrase: {phrase}")


def validate_symbol_reference(workflow_id: str, workflow: dict[str, Any], field: str, failures: list[str]) -> None:
    reference = workflow.get(field)
    if not isinstance(reference, dict):
        fail(failures, f"{workflow_id}: {field} must be an object")
        return
    path_value = reference.get("path")
    function_name = reference.get("function")
    if not isinstance(path_value, str) or not isinstance(function_name, str):
        fail(failures, f"{workflow_id}: {field}.path and {field}.function must be strings")
        return
    path = REPO_ROOT / path_value
    if not python_has_function(path, function_name, failures):
        fail(failures, f"{workflow_id}: missing function {function_name} in {path_value}")


def validate_class_reference(workflow_id: str, workflow: dict[str, Any], field: str, failures: list[str]) -> None:
    reference = workflow.get(field)
    if not isinstance(reference, dict):
        fail(failures, f"{workflow_id}: {field} must be an object")
        return
    path_value = reference.get("path")
    class_name = reference.get("class")
    if not isinstance(path_value, str) or not isinstance(class_name, str):
        fail(failures, f"{workflow_id}: {field}.path and {field}.class must be strings")
        return
    path = REPO_ROOT / path_value
    if not python_has_class(path, class_name, failures):
        fail(failures, f"{workflow_id}: missing class {class_name} in {path_value}")


def validate_implemented_workflow(workflow: dict[str, Any], failures: list[str]) -> None:
    workflow_id = str(workflow.get("id", "<missing-id>"))

    data_boundary_path = workflow.get("data_boundary_manifest")
    if not isinstance(data_boundary_path, str):
        fail(failures, f"{workflow_id}: data_boundary_manifest must be a string")
        data_boundary = {}
    else:
        data_boundary = load_json(REPO_ROOT / data_boundary_path, failures)

    if data_boundary:
        if data_boundary.get("workflow") != workflow.get("id"):
            fail(failures, f"{workflow_id}: data boundary workflow id mismatch")
        if data_boundary.get("proposal_type") != workflow.get("proposal_type"):
            fail(failures, f"{workflow_id}: data boundary proposal_type mismatch")
        required_policy = data_boundary.get("required_policy")
        if required_policy != workflow.get("policy"):
            fail(failures, f"{workflow_id}: data boundary policy mismatch")

    openapi_contract = workflow.get("openapi_contract")
    if not isinstance(openapi_contract, str):
        fail(failures, f"{workflow_id}: openapi_contract must be a string")
    else:
        openapi_text = read_text(REPO_ROOT / openapi_contract, failures)
        route = str(workflow.get("route", "")).split(" ", 1)[-1]
        if route and route not in openapi_text:
            fail(failures, f"{workflow_id}: OpenAPI contract missing route {route}")
        for snippet in (
            f"const: {workflow.get('proposal_type')}",
            "const: draft_only",
            "const: none",
            "additionalProperties: false",
        ):
            if snippet not in openapi_text:
                fail(failures, f"{workflow_id}: OpenAPI contract missing snippet {snippet!r}")

    for field in ("control_plane_handler", "control_plane_renderer", "payload_builder", "frappe_requester", "proposal_storage"):
        validate_symbol_reference(workflow_id, workflow, field, failures)
    if workflow.get("provider_mode") == "deterministic":
        # ADR-0009: deterministic workflows have no hosted provider surface; the
        # renderer named above is the production path and needs no live evaluation.
        for forbidden_field in ("production_provider_adapter", "production_provider_evaluation"):
            if forbidden_field in workflow:
                fail(failures, f"{workflow_id}: deterministic workflows must not declare {forbidden_field}")
    else:
        validate_symbol_reference(workflow_id, workflow, "production_provider_adapter", failures)
        validate_symbol_reference(workflow_id, workflow, "production_provider_evaluation", failures)
        evaluation = workflow.get("production_provider_evaluation")
        if isinstance(evaluation, dict):
            runbook = evaluation.get("runbook")
            if not isinstance(runbook, str) or not (REPO_ROOT / runbook).is_file():
                fail(failures, f"{workflow_id}: production provider evaluation runbook is missing: {runbook}")
    validate_class_reference(workflow_id, workflow, "request_model", failures)

    for field in ("docs", "tests"):
        for path_value in string_list(workflow.get(field), f"{workflow_id}.{field}", failures):
            if not (REPO_ROOT / path_value).is_file():
                fail(failures, f"{workflow_id}: {field} path is missing: {path_value}")

    docs_text = "\n".join(
        read_text(REPO_ROOT / path_value, failures)
        for path_value in workflow.get("docs", [])
        if isinstance(path_value, str)
    )
    tests_text = "\n".join(
        read_text(REPO_ROOT / path_value, failures)
        for path_value in workflow.get("tests", [])
        if isinstance(path_value, str)
    )
    for phrase in ("draft-only", "no ERP side effect", "human review"):
        if not contains_snippet(docs_text, phrase):
            fail(failures, f"{workflow_id}: workflow docs must mention {phrase!r}")
    for phrase in ("requested_action", "allowed_action", "Sales Invoice", "Stock Entry"):
        if not contains_snippet(tests_text, phrase):
            fail(failures, f"{workflow_id}: workflow tests must mention {phrase!r}")

    for command in string_list(workflow.get("proof_commands"), f"{workflow_id}.proof_commands", failures):
        first = command.split()[0]
        if first.startswith("scripts/") and not (REPO_ROOT / first).is_file():
            fail(failures, f"{workflow_id}: proof command references missing script: {first}")


def validate_workflows(registry: dict[str, Any], failures: list[str]) -> None:
    workflows = registry.get("workflows")
    if not isinstance(workflows, list):
        return
    implemented_count = 0
    for workflow in workflows:
        if not isinstance(workflow, dict):
            continue
        if workflow.get("status") == "implemented":
            implemented_count += 1
            validate_implemented_workflow(workflow, failures)
    if implemented_count < 1:
        fail(failures, "at least one implemented AI workflow is required for the MVP")


def main() -> int:
    failures: list[str] = []
    registry = load_json(REGISTRY_PATH, failures)

    if registry:
        validate_shape(registry, failures)
        validate_registry_docs(registry, failures)
        validate_workflows(registry, failures)

    if failures:
        print("AI workflow registry check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("AI workflow registry check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
