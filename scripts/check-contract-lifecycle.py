#!/usr/bin/env python3
"""Validate contract lifecycle/versioning policy consistency."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from _gate import REPO_ROOT, contains_snippet, load_json, read_text, rel


MANIFEST_PATH = REPO_ROOT / "config" / "contract-lifecycle.json"
CONTRACT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-v(?P<major>[1-9][0-9]*)$")
SEMVER_PATTERN = re.compile(r"^(?P<major>0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
EVENT_TYPE_PATTERN = re.compile(r"^\s+- (?P<event>ai_erp\.[a-z0-9_.]+\.v(?P<major>[1-9][0-9]*))\s*$")
CATALOG_REQUIRED_FIELDS = {
    "id",
    "kind",
    "status",
    "version",
    "path",
    "owner_area",
    "producer",
    "consumers",
    "safety_boundary",
    "tests",
    "verification",
}


def string_list(value: Any, field: str, failures: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        failures.append(f"{field} must be a non-empty list")
        return []
    result: list[str] = []
    for index, item in enumerate(value, 1):
        if not isinstance(item, str) or not item.strip():
            failures.append(f"{field}[{index}] must be a non-empty string")
            continue
        result.append(item)
    return result


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    for field in ("lifecycle_doc", "catalog", "contracts_readme", "events_readme"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{field} must be a non-empty string")
        elif not (REPO_ROOT / value).is_file():
            failures.append(f"{field} path is missing: {value}")

    status_flow = string_list(manifest.get("status_flow"), "status_flow", failures)
    if status_flow != ["planned", "contract-only", "implemented"]:
        failures.append("status_flow must be planned, contract-only, implemented")

    rules = manifest.get("kind_rules")
    if not isinstance(rules, dict):
        failures.append("kind_rules must be an object")
    else:
        for kind in ("openapi", "business-event"):
            if not isinstance(rules.get(kind), dict):
                failures.append(f"kind_rules.{kind} must be an object")

    for field in (
        "required_lifecycle_doc_phrases",
        "required_contracts_readme_phrases",
        "required_events_readme_phrases",
        "required_catalog_safety_terms",
    ):
        string_list(manifest.get(field), field, failures)


def validate_doc_phrases(manifest: dict[str, Any], failures: list[str]) -> None:
    checks = (
        ("lifecycle_doc", "required_lifecycle_doc_phrases"),
        ("contracts_readme", "required_contracts_readme_phrases"),
        ("events_readme", "required_events_readme_phrases"),
    )
    for path_field, phrase_field in checks:
        path_value = manifest.get(path_field)
        if not isinstance(path_value, str):
            continue
        text = read_text(REPO_ROOT / path_value, failures)
        for phrase in string_list(manifest.get(phrase_field), phrase_field, failures):
            if not contains_snippet(text, phrase):
                failures.append(f"{path_value}: missing contract lifecycle phrase: {phrase}")


def extract_openapi_version(contract_text: str) -> str | None:
    match = re.search(r"^\s*version:\s*['\"]?(?P<version>[0-9]+\.[0-9]+\.[0-9]+)['\"]?\s*$", contract_text, flags=re.MULTILINE)
    return match.group("version") if match else None


def extract_event_types(contract_text: str) -> list[tuple[str, str]]:
    event_types: list[tuple[str, str]] = []
    for line in contract_text.splitlines():
        match = EVENT_TYPE_PATTERN.match(line)
        if match:
            event_types.append((match.group("event"), match.group("major")))
    return event_types


def validate_contract_entry(
    manifest: dict[str, Any],
    contract: dict[str, Any],
    failures: list[str],
) -> None:
    contract_id = str(contract.get("id", "<missing-id>"))
    missing = sorted(CATALOG_REQUIRED_FIELDS - set(contract))
    if missing:
        failures.append(f"{contract_id}: missing required fields: {', '.join(missing)}")
    owner_area = contract.get("owner_area")
    if not isinstance(owner_area, str) or not owner_area.strip() or not (REPO_ROOT / owner_area).exists():
        failures.append(f"{contract_id}: owner_area must name an existing path")
    if not isinstance(contract.get("producer"), str) or not contract["producer"].strip():
        failures.append(f"{contract_id}: producer must be a non-empty string")
    for consumer in string_list(contract.get("consumers"), f"{contract_id}.consumers", failures):
        if not (REPO_ROOT / consumer).exists():
            failures.append(f"{contract_id}: consumer path does not exist: {consumer}")
    contract_name = Path(str(contract.get("path"))).name
    for test_path in string_list(contract.get("tests"), f"{contract_id}.tests", failures):
        if not (REPO_ROOT / test_path).is_file():
            failures.append(f"{contract_id}: test path does not exist: {test_path}")
        elif contract_name not in read_text(REPO_ROOT / test_path, failures):
            failures.append(f"{contract_id}: test {test_path} must reference {contract_name}")
    string_list(contract.get("verification"), f"{contract_id}.verification", failures)

    id_match = CONTRACT_ID_PATTERN.match(contract_id)
    if not id_match:
        failures.append(f"{contract_id}: id must end with -vN")
        return
    major = id_match.group("major")

    kind = contract.get("kind")
    status = contract.get("status")
    status_flow = set(string_list(manifest.get("status_flow"), "status_flow", failures))
    if status not in status_flow:
        failures.append(f"{contract_id}: status {status!r} is not allowed by contract lifecycle")

    kind_rules = manifest.get("kind_rules", {})
    kind_rule = kind_rules.get(kind) if isinstance(kind_rules, dict) else None
    if not isinstance(kind_rule, dict):
        failures.append(f"{contract_id}: missing lifecycle rule for kind {kind!r}")
        return

    path_value = contract.get("path")
    if not isinstance(path_value, str):
        failures.append(f"{contract_id}: path must be a string")
        return
    path_prefix = kind_rule.get("path_prefix")
    if isinstance(path_prefix, str) and not path_value.startswith(path_prefix):
        failures.append(f"{contract_id}: path must start with {path_prefix}")
    expected_suffix = f"-v{major}.yaml"
    if not path_value.endswith(expected_suffix):
        failures.append(f"{contract_id}: path must end with {expected_suffix}")

    version = contract.get("version")
    if not isinstance(version, str):
        failures.append(f"{contract_id}: version must be a string")
        return

    contract_text = read_text(REPO_ROOT / path_value, failures)
    if kind == "openapi":
        semver = SEMVER_PATTERN.match(version)
        if not semver:
            failures.append(f"{contract_id}: OpenAPI catalog version must be SemVer")
        elif semver.group("major") != major:
            failures.append(f"{contract_id}: OpenAPI catalog major version must match id")
        openapi_version = extract_openapi_version(contract_text)
        if openapi_version != version:
            failures.append(f"{contract_id}: OpenAPI info.version must match catalog version")
        if "openapi:" not in contract_text:
            failures.append(f"{contract_id}: OpenAPI contract must declare openapi")
        if "draft_only" not in contract_text or "allowed_action" not in contract_text:
            failures.append(f"{contract_id}: OpenAPI AI boundary must remain draft-only with allowed_action")
    elif kind == "business-event":
        if version != major:
            failures.append(f"{contract_id}: business-event catalog version must equal id major")
        if f"schema_version: {major}" not in contract_text:
            failures.append(f"{contract_id}: event schema_version must equal major version")
        event_types = extract_event_types(contract_text)
        if not event_types:
            failures.append(f"{contract_id}: must declare versioned event_types")
        for event_type, event_major in event_types:
            if event_major != major:
                failures.append(f"{contract_id}: event type major mismatch: {event_type}")
        if status == "contract-only" and "status: contract-only" not in contract_text:
            failures.append(f"{contract_id}: contract-only status must be visible in event contract")

    safety_boundary = str(contract.get("safety_boundary", "")).lower()
    for term in string_list(manifest.get("required_catalog_safety_terms"), "required_catalog_safety_terms", failures):
        if term not in safety_boundary:
            failures.append(f"{contract_id}: safety_boundary must mention {term}")

    verification = contract.get("verification")
    if status == "implemented":
        if not isinstance(verification, list) or not any(isinstance(item, str) and item.startswith("scripts/dev.sh ") for item in verification):
            failures.append(f"{contract_id}: implemented contracts need a scripts/dev.sh verification command")
    if status == "contract-only" and isinstance(contract.get("producer"), str):
        if "future" not in contract["producer"].lower():
            failures.append(f"{contract_id}: contract-only producer should identify future implementation ownership")


def validate_catalog(manifest: dict[str, Any], failures: list[str]) -> None:
    catalog_path = manifest.get("catalog")
    if not isinstance(catalog_path, str):
        return
    catalog = load_json(REPO_ROOT / catalog_path, failures)
    contracts = catalog.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        failures.append(f"{catalog_path}: contracts must be a non-empty list")
        return

    seen_ids: set[str] = set()
    cataloged_paths: set[str] = set()
    for entry in contracts:
        if not isinstance(entry, dict):
            failures.append(f"{catalog_path}: every contract entry must be an object")
            continue
        for field, seen in (("id", seen_ids), ("path", cataloged_paths)):
            value = entry.get(field)
            if isinstance(value, str):
                if value in seen:
                    failures.append(f"{catalog_path}: duplicate contract {field}: {value}")
                seen.add(value)
        validate_contract_entry(manifest, entry, failures)

    discovered = {
        rel(path)
        for folder in ("openapi", "events")
        for path in (REPO_ROOT / "contracts" / folder).glob("*.yaml")
    }
    if discovered != cataloged_paths:
        failures.append(
            f"{catalog_path}: contract files and catalog paths differ "
            f"(uncataloged: {sorted(discovered - cataloged_paths)}, missing files: {sorted(cataloged_paths - discovered)})",
        )


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_doc_phrases(manifest, failures)
        validate_catalog(manifest, failures)

    if failures:
        print("Contract lifecycle check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Contract lifecycle check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
