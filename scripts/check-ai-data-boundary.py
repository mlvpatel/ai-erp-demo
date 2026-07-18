#!/usr/bin/env python3
"""Validate the MVP AI data-sharing boundary."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "ai-data-boundary.json"
REGISTERED_MANIFESTS = (
    (REPO_ROOT / "config" / "ai-data-boundary-scheduling.json", "scheduling_explanation"),
    (REPO_ROOT / "config" / "ai-data-boundary-exception-recovery.json", "exception_recovery"),
)


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
    fields: set[str] = set()
    for node in module.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for child in node.body:
            if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                fields.add(child.target.id)
    return fields


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    if manifest.get("schema_version") != 1:
        fail(failures, "ai-data-boundary.json schema_version must be 1")
    if manifest.get("workflow") != "service_closeout_summary":
        fail(failures, "workflow must be service_closeout_summary for the MVP")
    if manifest.get("proposal_type") != "service_closeout_summary":
        fail(failures, "proposal_type must be service_closeout_summary")

    for field in ("payload_builder", "control_plane_models", "openapi_contract", "service_readme"):
        if field not in manifest:
            fail(failures, f"missing manifest field: {field}")

    allowed_fields = manifest.get("allowed_fields")
    if not isinstance(allowed_fields, dict):
        fail(failures, "allowed_fields must be an object")
        return
    for key in ("request", "work_order", "time_entry", "part_usage", "related_work", "source_reference", "source_fields"):
        value = allowed_fields.get(key)
        if not isinstance(value, list) or not value or any(not isinstance(item, str) for item in value):
            fail(failures, f"allowed_fields.{key} must be a non-empty list of strings")

    policy = manifest.get("required_policy")
    if not isinstance(policy, dict) or policy.get("decision") != "draft_only" or policy.get("allowed_action") != "none":
        fail(failures, "required_policy must be draft_only/none")


def validate_payload_builder(manifest: dict[str, Any], failures: list[str]) -> None:
    builder = manifest.get("payload_builder")
    if not isinstance(builder, dict):
        fail(failures, "payload_builder must be an object")
        return

    path_value = builder.get("path")
    function_name = builder.get("function")
    if not isinstance(path_value, str) or not isinstance(function_name, str):
        fail(failures, "payload_builder.path and payload_builder.function must be strings")
        return

    path = REPO_ROOT / path_value
    source_text = read_text(path, failures)
    module = parse_python(path, failures)
    if module is None:
        return
    function = find_function(module, function_name)
    if function is None:
        fail(failures, f"{path_value}: missing payload builder function {function_name}")
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
            fail(failures, f"{path_value}: {name} fields mismatch: expected={sorted(expected)} actual={sorted(actual or [])}")

    source_fields = source_field_literals(module)
    expected_source_fields = set(allowed["source_fields"])
    if source_fields != expected_source_fields:
        fail(
            failures,
            f"{path_value}: source field citations mismatch: expected={sorted(expected_source_fields)} actual={sorted(source_fields)}",
        )

    snippets = manifest.get("forbidden_payload_builder_snippets")
    if not isinstance(snippets, list):
        fail(failures, "forbidden_payload_builder_snippets must be a list")
    else:
        for snippet in snippets:
            if not isinstance(snippet, str):
                fail(failures, "forbidden payload builder snippets must be strings")
            elif snippet in source_text:
                fail(failures, f"{path_value}: forbidden payload builder snippet present: {snippet}")


def validate_models(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("control_plane_models")
    if not isinstance(path_value, str):
        fail(failures, "control_plane_models must be a string")
        return
    path = REPO_ROOT / path_value
    text_value = read_text(path, failures)
    module = parse_python(path, failures)
    if module is None:
        return

    if 'ConfigDict(extra="forbid")' not in text_value:
        fail(failures, f"{path_value}: strict models must forbid extra fields")

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
            fail(failures, f"{path_value}: {class_name} fields mismatch: expected={sorted(expected)} actual={sorted(actual)}")

    policy_fields = class_fields(module, "Policy")
    if "decision" not in policy_fields or "allowed_action" not in policy_fields:
        fail(failures, f"{path_value}: Policy must include decision and allowed_action")


def validate_openapi(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("openapi_contract")
    if not isinstance(path_value, str):
        fail(failures, "openapi_contract must be a string")
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
            fail(failures, f"{path_value}: missing required OpenAPI snippet {snippet!r}")

    forbidden = manifest.get("forbidden_payload_keys", [])
    for key in forbidden:
        if not isinstance(key, str):
            fail(failures, "forbidden_payload_keys entries must be strings")
            continue
        if re.search(rf"^\s{{8,}}{re.escape(key)}:\s*$", text_value, flags=re.MULTILINE):
            fail(failures, f"{path_value}: forbidden schema property appears: {key}")


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
            fail(failures, "required_doc_phrases entries must be strings")
        elif not contains_snippet(doc_text, phrase):
            fail(failures, f"AI data-boundary documentation phrase missing: {phrase}")

    test_text = "\n".join(
        read_text(REPO_ROOT / path, failures)
        for path in manifest.get("tests", [])
        if isinstance(path, str)
    )
    for phrase in manifest.get("required_test_phrases", []):
        if not isinstance(phrase, str):
            fail(failures, "required_test_phrases entries must be strings")
        elif not contains_snippet(test_text, phrase):
            fail(failures, f"AI data-boundary test phrase missing: {phrase}")


def validate_registered_manifest(path: Path, expected_workflow: str, failures: list[str]) -> None:
    """Validate one registered deterministic workflow manifest (ADR-0009 pattern)."""
    manifest = load_json(path, failures)
    if not manifest:
        return
    label = rel(path)
    if manifest.get("schema_version") != 1:
        fail(failures, f"{label}: schema_version must be 1")
    if manifest.get("workflow") != expected_workflow:
        fail(failures, f"{label}: workflow must be {expected_workflow}")
    if manifest.get("proposal_type") != expected_workflow:
        fail(failures, f"{label}: proposal_type must be {expected_workflow}")
    if manifest.get("provider_mode") != "deterministic":
        fail(failures, f"{label}: provider_mode must stay deterministic per ADR-0009")
    policy = manifest.get("required_policy")
    if not isinstance(policy, dict) or policy.get("decision") != "draft_only" or policy.get("allowed_action") != "none":
        fail(failures, f"{label}: required_policy must be draft_only/none")

    allowed = manifest.get("allowed_request_fields")
    if not isinstance(allowed, list) or not allowed or any(not isinstance(item, str) for item in allowed):
        fail(failures, f"{label}: allowed_request_fields must be a non-empty string list")
        return

    models_path = manifest.get("control_plane_models")
    request_class = manifest.get("request_class")
    if isinstance(models_path, str) and isinstance(request_class, str):
        module = parse_python(REPO_ROOT / models_path, failures)
        if module is not None:
            actual = class_fields(module, request_class)
            if actual != set(allowed):
                fail(
                    failures,
                    f"{models_path}: {request_class} fields mismatch: expected={sorted(allowed)} actual={sorted(actual)}",
                )
    else:
        fail(failures, f"{label}: control_plane_models and request_class must be strings")

    builder = manifest.get("payload_builder")
    if isinstance(builder, dict) and isinstance(builder.get("path"), str) and isinstance(builder.get("function"), str):
        module = parse_python(REPO_ROOT / builder["path"], failures)
        if module is not None:
            function = find_function(module, builder["function"])
            if function is None:
                fail(failures, f"{builder['path']}: missing payload builder function {builder['function']}")
            elif returned_dict_keys(function) != set(allowed):
                fail(failures, f"{builder['path']}: payload keys must match allowed_request_fields")
    else:
        fail(failures, f"{label}: payload_builder must name a path and function")

    contract_path = manifest.get("openapi_contract")
    route = manifest.get("route")
    if isinstance(contract_path, str) and isinstance(route, str):
        contract_text = read_text(REPO_ROOT / contract_path, failures)
        for snippet in (route, f"const: {expected_workflow}"):
            if snippet not in contract_text:
                fail(failures, f"{contract_path}: missing contract snippet {snippet!r}")
    else:
        fail(failures, f"{label}: openapi_contract and route must be strings")


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
    for registered_path, registered_workflow in REGISTERED_MANIFESTS:
        validate_registered_manifest(registered_path, registered_workflow, failures)

    if failures:
        print("AI data-boundary check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("AI data-boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
