#!/usr/bin/env python3
"""Validate connector and business-event integration safety guardrails."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "integration-safety.json"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def load_json(path: Path, failures: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(failures, f"missing JSON file: {rel(path)}")
    except json.JSONDecodeError as exc:
        fail(failures, f"invalid JSON in {rel(path)}: {exc}")
    return None


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


def required_path(manifest: dict[str, Any], field: str, failures: list[str]) -> str | None:
    value = manifest.get(field)
    if not isinstance(value, str) or not value.strip():
        fail(failures, f"{field} must be a non-empty string")
        return None
    if not (REPO_ROOT / value).exists():
        fail(failures, f"{field} path is missing: {value}")
    return value


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    if manifest.get("schema_version") != 1:
        fail(failures, "integration-safety.json schema_version must be 1")
    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        fail(failures, "description must be a non-empty string")

    for field in (
        "workflow_doc",
        "connector_readme",
        "contracts_readme",
        "events_readme",
        "contract_lifecycle_doc",
        "threat_model",
        "event_contract",
        "contract_catalog",
        "event_contract_tests",
        "reserved_connector_dir",
    ):
        required_path(manifest, field, failures)

    for field in (
        "reserved_connector_allowed_files",
        "connector_readme_required_phrases",
        "event_contract_required_snippets",
        "event_contract_forbidden_field_terms",
        "test_required_snippets",
        "required_doc_phrases",
    ):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            fail(failures, f"{field} must be a non-empty list")

    if not isinstance(manifest.get("catalog_event_contract"), dict):
        fail(failures, "catalog_event_contract must be an object")


def validate_reserved_connector(manifest: dict[str, Any], failures: list[str]) -> None:
    dir_value = manifest.get("reserved_connector_dir")
    if not isinstance(dir_value, str):
        return
    connector_dir = REPO_ROOT / dir_value
    allowed = set(string_list(manifest.get("reserved_connector_allowed_files"), "reserved_connector_allowed_files", failures))
    for path in connector_dir.rglob("*"):
        if path.is_dir():
            continue
        relative = str(path.relative_to(connector_dir))
        if relative not in allowed:
            fail(failures, f"{dir_value} must remain reserved; unexpected file: {relative}")

    readme_value = manifest.get("connector_readme")
    if isinstance(readme_value, str):
        readme_text = read_text(REPO_ROOT / readme_value, failures)
        for phrase in string_list(
            manifest.get("connector_readme_required_phrases"),
            "connector_readme_required_phrases",
            failures,
        ):
            if not contains_snippet(readme_text, phrase):
                fail(failures, f"{readme_value} missing connector rule: {phrase}")


def yaml_field_names(text: str) -> set[str]:
    names: set[str] = set()
    for line in text.splitlines():
        match = re.match(r"^\s{6,}([A-Za-z_][A-Za-z0-9_]*):\s*$", line)
        if match:
            names.add(match.group(1))
    return names


def validate_event_contract(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("event_contract")
    if not isinstance(path_value, str):
        return
    text = read_text(REPO_ROOT / path_value, failures)
    for snippet in string_list(manifest.get("event_contract_required_snippets"), "event_contract_required_snippets", failures):
        if not contains_snippet(text, snippet):
            fail(failures, f"{path_value} missing event-contract snippet: {snippet}")

    field_names = yaml_field_names(text)
    for term in string_list(
        manifest.get("event_contract_forbidden_field_terms"),
        "event_contract_forbidden_field_terms",
        failures,
    ):
        matched = sorted(field for field in field_names if term.lower() in field.lower())
        if matched:
            fail(failures, f"{path_value} has forbidden payload/envelope field term {term!r}: {', '.join(matched)}")


def validate_catalog(manifest: dict[str, Any], failures: list[str]) -> None:
    catalog_path = manifest.get("contract_catalog")
    spec = manifest.get("catalog_event_contract")
    if not isinstance(catalog_path, str) or not isinstance(spec, dict):
        return
    value = load_json(REPO_ROOT / catalog_path, failures)
    if not isinstance(value, dict):
        return
    contracts = value.get("contracts")
    if not isinstance(contracts, list):
        fail(failures, f"{catalog_path}: contracts must be a list")
        return
    expected_id = spec.get("id")
    entry = next(
        (contract for contract in contracts if isinstance(contract, dict) and contract.get("id") == expected_id),
        None,
    )
    if not isinstance(entry, dict):
        fail(failures, f"{catalog_path}: missing contract entry {expected_id}")
        return

    for field in ("kind", "status", "path"):
        expected = spec.get(field)
        if isinstance(expected, str) and entry.get(field) != expected:
            fail(failures, f"{expected_id}: expected catalog {field}={expected!r}")

    consumer = spec.get("consumer")
    consumers = entry.get("consumers")
    if isinstance(consumer, str) and (not isinstance(consumers, list) or consumer not in consumers):
        fail(failures, f"{expected_id}: catalog consumers must include {consumer}")

    producer_contains = spec.get("producer_contains")
    producer = entry.get("producer")
    if isinstance(producer_contains, str) and (
        not isinstance(producer, str) or producer_contains.lower() not in producer.lower()
    ):
        fail(failures, f"{expected_id}: catalog producer must mention {producer_contains}")

    boundary = str(entry.get("safety_boundary", ""))
    for term in string_list(spec.get("required_safety_terms"), "catalog_event_contract.required_safety_terms", failures):
        if term.lower() not in boundary.lower():
            fail(failures, f"{expected_id}: safety_boundary missing term: {term}")


def validate_tests(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("event_contract_tests")
    if not isinstance(path_value, str):
        return
    text = read_text(REPO_ROOT / path_value, failures)
    for snippet in string_list(manifest.get("test_required_snippets"), "test_required_snippets", failures):
        if not contains_snippet(text, snippet):
            fail(failures, f"{path_value} missing event-contract test snippet: {snippet}")


def validate_docs(manifest: dict[str, Any], failures: list[str]) -> None:
    doc_text = "\n".join(
        read_text(REPO_ROOT / path_value, failures)
        for path_value in (
            manifest.get("workflow_doc"),
            manifest.get("contracts_readme"),
            manifest.get("events_readme"),
            manifest.get("contract_lifecycle_doc"),
            manifest.get("threat_model"),
        )
        if isinstance(path_value, str)
    )
    for phrase in string_list(manifest.get("required_doc_phrases"), "required_doc_phrases", failures):
        if not contains_snippet(doc_text, phrase):
            fail(failures, f"integration safety docs missing phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    value = load_json(MANIFEST_PATH, failures)
    manifest = value if isinstance(value, dict) else {}

    if manifest:
        validate_shape(manifest, failures)
        validate_reserved_connector(manifest, failures)
        validate_event_contract(manifest, failures)
        validate_catalog(manifest, failures)
        validate_tests(manifest, failures)
        validate_docs(manifest, failures)

    if failures:
        print("Integration safety check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Integration safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
