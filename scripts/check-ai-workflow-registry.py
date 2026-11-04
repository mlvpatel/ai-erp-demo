#!/usr/bin/env python3
"""Validate AI workflow registry, lifecycle docs, and implemented workflow proofs."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from _gate import REPO_ROOT, contains_snippet, load_json, parse_python, read_text, report, string_list


REGISTRY_PATH = REPO_ROOT / "config" / "ai-workflow-registry.json"
ALLOWED_STATUSES = {"proposed", "approved_for_implementation", "implemented"}
ALLOWED_PROVIDER_MODES = {"deterministic", "openai"}
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
ROUTE_PATTERN = re.compile(r"^(GET|POST|PUT|PATCH|DELETE) /[A-Za-z0-9/_{}.-]+$")
OPENAPI_PROPOSAL_PATH_PATTERN = re.compile(r"""^[ \t]+["']?(/v1/proposals/[^\s:"']+)["']?:[ \t]*$""", re.MULTILINE)


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
    for field in ("lifecycle_doc", "review_checklist", "threat_model"):
        value = registry.get(field)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{field} must be a non-empty string")
        elif not (REPO_ROOT / value).is_file():
            failures.append(f"{field} path is missing: {value}")

    for field in ("required_lifecycle_doc_phrases", "required_review_doc_phrases"):
        string_list(registry.get(field), field, failures)

    workflows = registry.get("workflows")
    if not isinstance(workflows, list) or not workflows:
        failures.append("workflows must be a non-empty list")
        return

    seen_ids: set[str] = set()
    for index, workflow in enumerate(workflows, 1):
        if not isinstance(workflow, dict):
            failures.append(f"workflows[{index}] must be an object")
            continue
        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, str) or not ID_PATTERN.match(workflow_id):
            failures.append(f"workflows[{index}].id must be snake_case")
        elif workflow_id in seen_ids:
            failures.append(f"{workflow_id}: duplicate AI workflow id")
        else:
            seen_ids.add(workflow_id)

        status = workflow.get("status")
        if status not in ALLOWED_STATUSES:
            failures.append(f"{workflow_id}: status must be one of {', '.join(sorted(ALLOWED_STATUSES))}")
        if workflow.get("provider_mode") not in ALLOWED_PROVIDER_MODES:
            failures.append(
                f"{workflow_id}: provider_mode must be declared as one of {', '.join(sorted(ALLOWED_PROVIDER_MODES))}"
            )
        route = workflow.get("route")
        if not isinstance(route, str) or not ROUTE_PATTERN.match(route):
            failures.append(f"{workflow_id}: route must look like 'POST /path'")
        if not isinstance(workflow.get("proposal_type"), str) or not workflow["proposal_type"].strip():
            failures.append(f"{workflow_id}: proposal_type must be a non-empty string")

        policy = workflow.get("policy")
        if not isinstance(policy, dict):
            failures.append(f"{workflow_id}: policy must be an object")
        elif policy.get("decision") != "draft_only" or policy.get("allowed_action") != "none":
            failures.append(f"{workflow_id}: MVP AI policy must be draft_only/none")

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
                failures.append(f"{path_value}: missing AI workflow registry phrase: {phrase}")


def validate_symbol_reference(workflow_id: str, workflow: dict[str, Any], field: str, failures: list[str]) -> None:
    reference = workflow.get(field)
    if not isinstance(reference, dict):
        failures.append(f"{workflow_id}: {field} must be an object")
        return
    path_value = reference.get("path")
    function_name = reference.get("function")
    if not isinstance(path_value, str) or not isinstance(function_name, str):
        failures.append(f"{workflow_id}: {field}.path and {field}.function must be strings")
        return
    path = REPO_ROOT / path_value
    if not python_has_function(path, function_name, failures):
        failures.append(f"{workflow_id}: missing function {function_name} in {path_value}")


def validate_class_reference(workflow_id: str, workflow: dict[str, Any], field: str, failures: list[str]) -> None:
    reference = workflow.get(field)
    if not isinstance(reference, dict):
        failures.append(f"{workflow_id}: {field} must be an object")
        return
    path_value = reference.get("path")
    class_name = reference.get("class")
    if not isinstance(path_value, str) or not isinstance(class_name, str):
        failures.append(f"{workflow_id}: {field}.path and {field}.class must be strings")
        return
    path = REPO_ROOT / path_value
    if not python_has_class(path, class_name, failures):
        failures.append(f"{workflow_id}: missing class {class_name} in {path_value}")


def handler_reaches_hosted_provider(path: Path, function_name: str, failures: list[str]) -> bool | None:
    """True when the handler names the openai provider or calls a render_openai* adapter; None if not found."""
    module = parse_python(path, failures)
    if module is None:
        return None
    for node in module.body:
        if not (isinstance(node, ast.FunctionDef) and node.name == function_name):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and child.value == "openai":
                return True
            if isinstance(child, ast.Call):
                func = child.func
                name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
                if name.startswith("render_openai"):
                    return True
        return False
    return None


def validate_provider_mode_dispatch(workflow_id: str, workflow: dict[str, Any], failures: list[str]) -> None:
    """The declared provider_mode must match what the app.py handler dispatches to."""
    provider_mode = workflow.get("provider_mode")
    handler = workflow.get("control_plane_handler")
    if provider_mode not in ALLOWED_PROVIDER_MODES or not isinstance(handler, dict):
        return
    path_value = handler.get("path")
    function_name = handler.get("function")
    if not isinstance(path_value, str) or not isinstance(function_name, str):
        return
    reaches_provider = handler_reaches_hosted_provider(REPO_ROOT / path_value, function_name, failures)
    if reaches_provider is None:
        return
    if provider_mode == "deterministic" and reaches_provider:
        failures.append(
            f"{workflow_id}: declared deterministic but handler {function_name} in {path_value} "
            "dispatches to a hosted provider"
        )
    if provider_mode == "openai" and not reaches_provider:
        failures.append(
            f"{workflow_id}: declared provider_mode openai but handler {function_name} in {path_value} "
            "has no openai dispatch"
        )


def validate_contract_route_coverage(registry: dict[str, Any], failures: list[str]) -> None:
    """Every proposal path in an OpenAPI contract needs a registry entry, not only the reverse."""
    workflows = registry.get("workflows")
    if not isinstance(workflows, list):
        return
    workflows = [item for item in workflows if isinstance(item, dict)]
    registered = {str(item.get("route", "")).split(" ", 1)[-1] for item in workflows}
    contracts = {item["openapi_contract"] for item in workflows if isinstance(item.get("openapi_contract"), str)}
    for contract in sorted(contracts):
        for match in OPENAPI_PROPOSAL_PATH_PATTERN.finditer(read_text(REPO_ROOT / contract, failures)):
            if match.group(1) not in registered:
                failures.append(f"{contract}: proposal route {match.group(1)} has no ai-workflow-registry entry")


def validate_implemented_workflow(workflow: dict[str, Any], failures: list[str]) -> None:
    workflow_id = str(workflow.get("id", "<missing-id>"))

    data_boundary_path = workflow.get("data_boundary_manifest")
    data_boundary: dict[str, Any] = {}
    if workflow.get("provider_mode") == "deterministic":
        string_list(workflow.get("allowed_request_fields"), f"{workflow_id}.allowed_request_fields", failures)
    elif not isinstance(data_boundary_path, str):
        failures.append(f"{workflow_id}: data_boundary_manifest must be a string")
    else:
        data_boundary = load_json(REPO_ROOT / data_boundary_path, failures)

    if data_boundary:
        if data_boundary.get("workflow") != workflow.get("id"):
            failures.append(f"{workflow_id}: data boundary workflow id mismatch")
        if data_boundary.get("proposal_type") != workflow.get("proposal_type"):
            failures.append(f"{workflow_id}: data boundary proposal_type mismatch")
        required_policy = data_boundary.get("required_policy")
        if required_policy != workflow.get("policy"):
            failures.append(f"{workflow_id}: data boundary policy mismatch")

    openapi_contract = workflow.get("openapi_contract")
    if not isinstance(openapi_contract, str):
        failures.append(f"{workflow_id}: openapi_contract must be a string")
    else:
        openapi_text = read_text(REPO_ROOT / openapi_contract, failures)
        route = str(workflow.get("route", "")).split(" ", 1)[-1]
        if route and route not in openapi_text:
            failures.append(f"{workflow_id}: OpenAPI contract missing route {route}")
        for snippet in (
            f"const: {workflow.get('proposal_type')}",
            "const: draft_only",
            "const: none",
            "additionalProperties: false",
        ):
            if snippet not in openapi_text:
                failures.append(f"{workflow_id}: OpenAPI contract missing snippet {snippet!r}")

    for field in ("control_plane_handler", "control_plane_renderer", "payload_builder", "frappe_requester", "proposal_storage"):
        validate_symbol_reference(workflow_id, workflow, field, failures)
    validate_provider_mode_dispatch(workflow_id, workflow, failures)
    if workflow.get("provider_mode") == "deterministic":
        # ADR-0009: deterministic workflows have no hosted provider surface; the
        # renderer named above is the production path and needs no live evaluation.
        for forbidden_field in ("production_provider_adapter", "production_provider_evaluation"):
            if forbidden_field in workflow:
                failures.append(f"{workflow_id}: deterministic workflows must not declare {forbidden_field}")
    else:
        validate_symbol_reference(workflow_id, workflow, "production_provider_adapter", failures)
        validate_symbol_reference(workflow_id, workflow, "production_provider_evaluation", failures)
        evaluation = workflow.get("production_provider_evaluation")
        if isinstance(evaluation, dict):
            runbook = evaluation.get("runbook")
            if not isinstance(runbook, str) or not (REPO_ROOT / runbook).is_file():
                failures.append(f"{workflow_id}: production provider evaluation runbook is missing: {runbook}")
    validate_class_reference(workflow_id, workflow, "request_model", failures)

    for field in ("docs", "tests"):
        for path_value in string_list(workflow.get(field), f"{workflow_id}.{field}", failures):
            if not (REPO_ROOT / path_value).is_file():
                failures.append(f"{workflow_id}: {field} path is missing: {path_value}")

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
            failures.append(f"{workflow_id}: workflow docs must mention {phrase!r}")
    for phrase in ("requested_action", "allowed_action", "Sales Invoice", "Stock Entry"):
        if not contains_snippet(tests_text, phrase):
            failures.append(f"{workflow_id}: workflow tests must mention {phrase!r}")

    for command in string_list(workflow.get("proof_commands"), f"{workflow_id}.proof_commands", failures):
        first = command.split()[0]
        if first.startswith("scripts/") and not (REPO_ROOT / first).is_file():
            failures.append(f"{workflow_id}: proof command references missing script: {first}")


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
        failures.append("at least one implemented AI workflow is required for the MVP")


def main() -> int:
    failures: list[str] = []
    registry = load_json(REGISTRY_PATH, failures)

    if registry:
        validate_shape(registry, failures)
        validate_registry_docs(registry, failures)
        validate_workflows(registry, failures)
        validate_contract_route_coverage(registry, failures)

    return report("AI workflow registry check", failures)


if __name__ == "__main__":
    raise SystemExit(main())
