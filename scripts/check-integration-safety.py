#!/usr/bin/env python3
"""Validate connector and business-event integration safety guardrails."""

from __future__ import annotations

import re
import sys
from typing import Any

from _gate import (
    REPO_ROOT,
    contains_snippet,
    joined_doc_phrases,
    load_json,
    load_json_object,
    read_text,
    string_list,
)


MANIFEST_PATH = REPO_ROOT / "config" / "integration-safety.json"
DOC_FIELDS = ("workflow_doc", "contracts_readme", "events_readme", "contract_lifecycle_doc", "threat_model")


def required_path(manifest: dict[str, Any], field: str, failures: list[str]) -> str | None:
    value = manifest.get(field)
    if not isinstance(value, str) or not value.strip():
        failures.append(f"{field} must be a non-empty string")
        return None
    if not (REPO_ROOT / value).exists():
        failures.append(f"{field} path is missing: {value}")
    return value


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
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
            failures.append(f"{field} must be a non-empty list")

    if not isinstance(manifest.get("catalog_event_contract"), dict):
        failures.append("catalog_event_contract must be an object")


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
            failures.append(f"{dir_value} must remain reserved; unexpected file: {relative}")

    readme_value = manifest.get("connector_readme")
    if isinstance(readme_value, str):
        readme_text = read_text(REPO_ROOT / readme_value, failures)
        for phrase in string_list(
            manifest.get("connector_readme_required_phrases"),
            "connector_readme_required_phrases",
            failures,
        ):
            if not contains_snippet(readme_text, phrase):
                failures.append(f"{readme_value} missing connector rule: {phrase}")


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
            failures.append(f"{path_value} missing event-contract snippet: {snippet}")

    field_names = yaml_field_names(text)
    for term in string_list(
        manifest.get("event_contract_forbidden_field_terms"),
        "event_contract_forbidden_field_terms",
        failures,
    ):
        matched = sorted(field for field in field_names if term.lower() in field.lower())
        if matched:
            failures.append(f"{path_value} has forbidden payload/envelope field term {term!r}: {', '.join(matched)}")


def validate_catalog(manifest: dict[str, Any], failures: list[str]) -> None:
    catalog_path = manifest.get("contract_catalog")
    spec = manifest.get("catalog_event_contract")
    if not isinstance(catalog_path, str) or not isinstance(spec, dict):
        return
    value = load_json_object(REPO_ROOT / catalog_path, failures)
    if not isinstance(value, dict):
        return
    contracts = value.get("contracts")
    if not isinstance(contracts, list):
        failures.append(f"{catalog_path}: contracts must be a list")
        return
    expected_id = spec.get("id")
    entry = next(
        (contract for contract in contracts if isinstance(contract, dict) and contract.get("id") == expected_id),
        None,
    )
    if not isinstance(entry, dict):
        failures.append(f"{catalog_path}: missing contract entry {expected_id}")
        return

    for field in ("kind", "status", "path"):
        expected = spec.get(field)
        if isinstance(expected, str) and entry.get(field) != expected:
            failures.append(f"{expected_id}: expected catalog {field}={expected!r}")

    consumer = spec.get("consumer")
    consumers = entry.get("consumers")
    if isinstance(consumer, str) and (not isinstance(consumers, list) or consumer not in consumers):
        failures.append(f"{expected_id}: catalog consumers must include {consumer}")

    producer_contains = spec.get("producer_contains")
    producer = entry.get("producer")
    if isinstance(producer_contains, str) and (
        not isinstance(producer, str) or producer_contains.lower() not in producer.lower()
    ):
        failures.append(f"{expected_id}: catalog producer must mention {producer_contains}")

    boundary = str(entry.get("safety_boundary", ""))
    for term in string_list(spec.get("required_safety_terms"), "catalog_event_contract.required_safety_terms", failures):
        if term.lower() not in boundary.lower():
            failures.append(f"{expected_id}: safety_boundary missing term: {term}")


def validate_tests(manifest: dict[str, Any], failures: list[str]) -> None:
    path_value = manifest.get("event_contract_tests")
    if not isinstance(path_value, str):
        return
    text = read_text(REPO_ROOT / path_value, failures)
    for snippet in string_list(manifest.get("test_required_snippets"), "test_required_snippets", failures):
        if not contains_snippet(text, snippet):
            failures.append(f"{path_value} missing event-contract test snippet: {snippet}")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_reserved_connector(manifest, failures)
        validate_event_contract(manifest, failures)
        validate_catalog(manifest, failures)
        validate_tests(manifest, failures)
        joined_doc_phrases(manifest, DOC_FIELDS, "integration safety", failures)

    if failures:
        print("Integration safety check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Integration safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
