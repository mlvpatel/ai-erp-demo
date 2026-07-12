#!/usr/bin/env python3
"""Validate contract lifecycle/versioning policy consistency."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "contract-lifecycle.json"
CONTRACT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-v(?P<major>[1-9][0-9]*)$")
SEMVER_PATTERN = re.compile(r"^(?P<major>0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
EVENT_TYPE_PATTERN = re.compile(r"^\s+- (?P<event>ai_erp\.[a-z0-9_.]+\.v(?P<major>[1-9][0-9]*))\s*$")


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


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    if manifest.get("schema_version") != 1:
        fail(failures, "contract-lifecycle.json schema_version must be 1")

    for field in ("lifecycle_doc", "catalog", "contracts_readme", "events_readme"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            fail(failures, f"{field} must be a non-empty string")
        elif not (REPO_ROOT / value).is_file():
            fail(failures, f"{field} path is missing: {value}")

    status_flow = string_list(manifest.get("status_flow"), "status_flow", failures)
    if status_flow != ["planned", "contract-only", "implemented"]:
        fail(failures, "status_flow must be planned, contract-only, implemented")

    rules = manifest.get("kind_rules")
    if not isinstance(rules, dict):
        fail(failures, "kind_rules must be an object")
    else:
        for kind in ("openapi", "business-event"):
            if not isinstance(rules.get(kind), dict):
                fail(failures, f"kind_rules.{kind} must be an object")

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
                fail(failures, f"{path_value}: missing contract lifecycle phrase: {phrase}")


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
    id_match = CONTRACT_ID_PATTERN.match(contract_id)
    if not id_match:
        fail(failures, f"{contract_id}: id must end with -vN")
        return
    major = id_match.group("major")

    kind = contract.get("kind")
    status = contract.get("status")
    status_flow = set(string_list(manifest.get("status_flow"), "status_flow", failures))
    if status not in status_flow:
        fail(failures, f"{contract_id}: status {status!r} is not allowed by contract lifecycle")

    kind_rules = manifest.get("kind_rules", {})
    kind_rule = kind_rules.get(kind) if isinstance(kind_rules, dict) else None
    if not isinstance(kind_rule, dict):
        fail(failures, f"{contract_id}: missing lifecycle rule for kind {kind!r}")
        return

    path_value = contract.get("path")
    if not isinstance(path_value, str):
        fail(failures, f"{contract_id}: path must be a string")
        return
    path_prefix = kind_rule.get("path_prefix")
    if isinstance(path_prefix, str) and not path_value.startswith(path_prefix):
        fail(failures, f"{contract_id}: path must start with {path_prefix}")
    expected_suffix = f"-v{major}.yaml"
    if not path_value.endswith(expected_suffix):
        fail(failures, f"{contract_id}: path must end with {expected_suffix}")

    version = contract.get("version")
    if not isinstance(version, str):
        fail(failures, f"{contract_id}: version must be a string")
        return

    contract_text = read_text(REPO_ROOT / path_value, failures)
    if kind == "openapi":
        semver = SEMVER_PATTERN.match(version)
        if not semver:
            fail(failures, f"{contract_id}: OpenAPI catalog version must be SemVer")
        elif semver.group("major") != major:
            fail(failures, f"{contract_id}: OpenAPI catalog major version must match id")
        openapi_version = extract_openapi_version(contract_text)
        if openapi_version != version:
            fail(failures, f"{contract_id}: OpenAPI info.version must match catalog version")
    elif kind == "business-event":
        if version != major:
            fail(failures, f"{contract_id}: business-event catalog version must equal id major")
        if f"schema_version: {major}" not in contract_text:
            fail(failures, f"{contract_id}: event schema_version must equal major version")
        event_types = extract_event_types(contract_text)
        if not event_types:
            fail(failures, f"{contract_id}: must declare versioned event_types")
        for event_type, event_major in event_types:
            if event_major != major:
                fail(failures, f"{contract_id}: event type major mismatch: {event_type}")

    safety_boundary = str(contract.get("safety_boundary", "")).lower()
    for term in string_list(manifest.get("required_catalog_safety_terms"), "required_catalog_safety_terms", failures):
        if term not in safety_boundary:
            fail(failures, f"{contract_id}: safety_boundary must mention {term}")

    verification = contract.get("verification")
    if status == "implemented":
        if not isinstance(verification, list) or not any(isinstance(item, str) and item.startswith("scripts/dev.sh ") for item in verification):
            fail(failures, f"{contract_id}: implemented contracts need a scripts/dev.sh verification command")
    if status == "contract-only" and isinstance(contract.get("producer"), str):
        if "future" not in contract["producer"].lower():
            fail(failures, f"{contract_id}: contract-only producer should identify future implementation ownership")


def validate_catalog(manifest: dict[str, Any], failures: list[str]) -> None:
    catalog_path = manifest.get("catalog")
    if not isinstance(catalog_path, str):
        return
    catalog = load_json(REPO_ROOT / catalog_path, failures)
    contracts = catalog.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        fail(failures, f"{catalog_path}: contracts must be a non-empty list")
        return

    for entry in contracts:
        if not isinstance(entry, dict):
            fail(failures, f"{catalog_path}: every contract entry must be an object")
            continue
        validate_contract_entry(manifest, entry, failures)


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
