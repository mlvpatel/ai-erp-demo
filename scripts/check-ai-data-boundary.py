#!/usr/bin/env python3
"""Validate the MVP AI data-sharing boundary."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Any

from _gate import REPO_ROOT, load_json, read_text, rel


MANIFEST_PATH = REPO_ROOT / "config" / "ai-data-boundary.json"
REGISTRY_PATH = REPO_ROOT / "config" / "ai-workflow-registry.json"
DETERMINISTIC_WORKFLOWS = ("scheduling_explanation", "exception_recovery", "repair_memory")


def parse_python(path: Path, failures: list[str]) -> ast.Module | None:
    source = read_text(path, failures)
    if not source:
        return None
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        failures.append(f"invalid Python in {rel(path)}: {exc}")
        return None


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def contains_snippet(haystack: str, needle: str) -> bool:
    return normalize_space(needle) in normalize_space(haystack)


def literal_dict_keys(node: ast.AST) -> set[str] | None:
    if not isinstance(node, ast.Dict):
        return None
    keys: set[str] = set()
    for key in node.keys:
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            return None
        keys.add(key.value)
    return keys


def find_function(module: ast.Module, function_name: str) -> ast.FunctionDef | None:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node
    return None


def assigned_dict_keys(function: ast.FunctionDef, variable: str) -> set[str] | None:
    for node in ast.walk(function):
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == variable for target in node.targets):
                if isinstance(node.value, ast.ListComp):
                    return literal_dict_keys(node.value.elt)
                return literal_dict_keys(node.value)
    return None


def returned_dict_keys(function: ast.FunctionDef) -> set[str] | None:
    for node in ast.walk(function):
        if isinstance(node, ast.Return):
            return literal_dict_keys(node.value)
    return None


def source_field_literals(module: ast.Module) -> set[str]:
    fields: set[str] = set()
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Name) and function.id == "_source" and len(node.args) >= 3:
            field = node.args[2]
            if isinstance(field, ast.Constant) and isinstance(field.value, str):
                fields.add(field.value)
    return fields


def class_fields(module: ast.Module, class_name: str) -> set[str]:
    """Annotated fields of a class, including those inherited from classes in the same module."""
    fields: set[str] = set()
    for node in module.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for child in node.body:
            if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                fields.add(child.target.id)
        for base in node.bases:
            if isinstance(base, ast.Name):
                fields |= class_fields(module, base.id)
    return fields


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    if manifest.get("workflow") != "service_closeout_summary":
        failures.append("workflow must be service_closeout_summary for the MVP")
    if manifest.get("proposal_type") != "service_closeout_summary":
        failures.append("proposal_type must be service_closeout_summary")

    for field in ("payload_builder", "control_plane_models", "openapi_contract", "service_readme"):
        if field not in manifest:
            failures.append(f"missing manifest field: {field}")

    allowed_fields = manifest.get("allowed_fields")
    if not isinstance(allowed_fields, dict):
        failures.append("allowed_fields must be an object")
        return
    for key in ("request", "work_order", "time_entry", "part_usage", "related_work", "source_reference", "source_fields"):
        value = allowed_fields.get(key)
        if not isinstance(value, list) or not value or any(not isinstance(item, str) for item in value):
            failures.append(f"allowed_fields.{key} must be a non-empty list of strings")

    policy = manifest.get("required_policy")
    if not isinstance(policy, dict) or policy.get("decision") != "draft_only" or policy.get("allowed_action") != "none":
        failures.append("required_policy must be draft_only/none")


def validate_payload_builder(manifest: dict[str, Any], failures: list[str]) -> None:
    builder = manifest.get("payload_builder")
    if not isinstance(builder, dict):
        failures.append("payload_builder must be an object")
        return

    path_value = builder.get("path")
    function_name = builder.get("function")
    if not isinstance(path_value, str) or not isinstance(function_name, str):
        failures.append("payload_builder.path and payload_builder.function must be strings")
        return

    path = REPO_ROOT / path_value
    source_text = read_text(path, failures)
    module = parse_python(path, failures)
    if module is None:
        return
    function = find_function(module, function_name)
    if function is None:
        failures.append(f"{path_value}: missing payload builder function {function_name}")
        return

    allowed = manifest["allowed_fields"]
    checks = {
        "request": returned_dict_keys(function),
        "work_order": assigned_dict_keys(function, "work_order_payload"),
        "time_entry": assigned_dict_keys(function, "time_entries"),
        "part_usage": assigned_dict_keys(function, "parts"),
        "related_work": assigned_dict_keys(function, "related_history"),
    }
    for name, actual in checks.items():
        expected = set(allowed[name])
        if actual != expected:
            failures.append(f"{path_value}: {name} fields mismatch: expected={sorted(expected)} actual={sorted(actual or [])}")

    source_fields = source_field_literals(module)
    expected_source_fields = set(allowed["source_fields"])
    if source_fields != expected_source_fields:
        failures.append(
            f"{path_value}: source field citations mismatch: expected={sorted(expected_source_fields)} actual={sorted(source_fields)}",
        )

    snippets = manifest.get("forbidden_payload_builder_snippets")
    if not isinstance(snippets, list):
        failures.append("forbidden_payload_builder_snippets must be a list")
    else:
        for snippet in snippets:
            if not isinstance(snippet, str):
                failures.append("forbidden payload builder snippets must be strings")
            elif snippet in source_text:
                failures.append(f"{path_value}: forbidden payload builder snippet present: {snippet}")


def validate_models(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("control_plane_models")
    if not isinstance(path_value, str):
        failures.append("control_plane_models must be a string")
        return
    path = REPO_ROOT / path_value
    text_value = read_text(path, failures)
    module = parse_python(path, failures)
    if module is None:
        return

    if 'ConfigDict(extra="forbid")' not in text_value:
        failures.append(f"{path_value}: strict models must forbid extra fields")

    allowed = manifest["allowed_fields"]
    class_map = {
        "ServiceCloseoutSummaryRequest": "request",
        "ServiceWorkOrder": "work_order",
        "TimeEntry": "time_entry",
        "PartUsage": "part_usage",
        "RelatedWorkSummary": "related_work",
        "SourceReference": "source_reference",
    }
    for class_name, key in class_map.items():
        actual = class_fields(module, class_name)
        expected = set(allowed[key])
        if actual != expected:
            failures.append(f"{path_value}: {class_name} fields mismatch: expected={sorted(expected)} actual={sorted(actual)}")

    policy_fields = class_fields(module, "Policy")
    if "decision" not in policy_fields or "allowed_action" not in policy_fields:
        failures.append(f"{path_value}: Policy must include decision and allowed_action")


def validate_openapi(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("openapi_contract")
    if not isinstance(path_value, str):
        failures.append("openapi_contract must be a string")
        return
    text_value = read_text(REPO_ROOT / path_value, failures)
    if not text_value:
        return

    for snippet in (
        "additionalProperties: false",
        "const: service_closeout_summary",
        "const: draft_only",
        "const: none",
        "ControlPlaneServiceKey",
    ):
        if snippet not in text_value:
            failures.append(f"{path_value}: missing required OpenAPI snippet {snippet!r}")

    forbidden = manifest.get("forbidden_payload_keys", [])
    for key in forbidden:
        if not isinstance(key, str):
            failures.append("forbidden_payload_keys entries must be strings")
            continue
        if re.search(rf"^\s{{8,}}{re.escape(key)}:\s*$", text_value, flags=re.MULTILINE):
            failures.append(f"{path_value}: forbidden schema property appears: {key}")


def validate_docs_and_tests(manifest: dict[str, Any], failures: list[str]) -> None:
    doc_paths = [manifest.get("service_readme")]
    doc_paths.extend(manifest.get("security_docs", []))
    doc_text = "\n".join(
        read_text(REPO_ROOT / path, failures)
        for path in doc_paths
        if isinstance(path, str)
    )
    for phrase in manifest.get("required_doc_phrases", []):
        if not isinstance(phrase, str):
            failures.append("required_doc_phrases entries must be strings")
        elif not contains_snippet(doc_text, phrase):
            failures.append(f"AI data-boundary documentation phrase missing: {phrase}")

    test_text = "\n".join(
        read_text(REPO_ROOT / path, failures)
        for path in manifest.get("tests", [])
        if isinstance(path, str)
    )
    for phrase in manifest.get("required_test_phrases", []):
        if not isinstance(phrase, str):
            failures.append("required_test_phrases entries must be strings")
        elif not contains_snippet(test_text, phrase):
            failures.append(f"AI data-boundary test phrase missing: {phrase}")


def validate_registered_workflow(workflow_id: str, workflow: dict[str, Any], failures: list[str]) -> None:
    """Validate one deterministic registry workflow's request boundary (ADR-0009 pattern)."""
    label = f"{rel(REGISTRY_PATH)} {workflow_id}"
    if workflow.get("proposal_type") != workflow_id:
        failures.append(f"{label}: proposal_type must be {workflow_id}")
    if workflow.get("provider_mode") != "deterministic":
        failures.append(f"{label}: provider_mode must stay deterministic per ADR-0009")

    allowed = workflow.get("allowed_request_fields")
    if not isinstance(allowed, list) or not allowed or any(not isinstance(item, str) for item in allowed):
        failures.append(f"{label}: allowed_request_fields must be a non-empty string list")
        return

    model = workflow.get("request_model")
    if isinstance(model, dict) and isinstance(model.get("path"), str) and isinstance(model.get("class"), str):
        module = parse_python(REPO_ROOT / model["path"], failures)
        if module is not None:
            actual = class_fields(module, model["class"])
            if actual != set(allowed):
                failures.append(
                    f"{model['path']}: {model['class']} fields mismatch: expected={sorted(allowed)} actual={sorted(actual)}",
                )
    else:
        failures.append(f"{label}: request_model must name a path and class")

    builder = workflow.get("payload_builder")
    if isinstance(builder, dict) and isinstance(builder.get("path"), str) and isinstance(builder.get("function"), str):
        module = parse_python(REPO_ROOT / builder["path"], failures)
        if module is not None:
            function = find_function(module, builder["function"])
            if function is None:
                failures.append(f"{builder['path']}: missing payload builder function {builder['function']}")
            elif returned_dict_keys(function) != set(allowed):
                failures.append(f"{builder['path']}: payload keys must match allowed_request_fields")
    else:
        failures.append(f"{label}: payload_builder must name a path and function")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        if isinstance(manifest.get("allowed_fields"), dict):
            validate_payload_builder(manifest, failures)
            validate_models(manifest, failures)
            validate_openapi(manifest, failures)
            validate_docs_and_tests(manifest, failures)
    registry = load_json(REGISTRY_PATH, failures)
    workflows = registry.get("workflows")
    by_id = {item.get("id"): item for item in workflows if isinstance(item, dict)} if isinstance(workflows, list) else {}
    for workflow_id in DETERMINISTIC_WORKFLOWS:
        workflow = by_id.get(workflow_id)
        if workflow is None:
            failures.append(f"{rel(REGISTRY_PATH)}: missing deterministic workflow {workflow_id}")
        else:
            validate_registered_workflow(workflow_id, workflow, failures)

    if failures:
        print("AI data-boundary check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("AI data-boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
