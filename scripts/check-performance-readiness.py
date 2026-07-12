#!/usr/bin/env python3
"""Validate performance and scalability readiness guardrails."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "performance-readiness.json"


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
    except UnicodeDecodeError as exc:
        fail(failures, f"expected UTF-8 text file: {rel(path)}: {exc}")
        return ""


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def contains_snippet(haystack: str, needle: str) -> bool:
    return normalize_space(needle) in normalize_space(haystack)


def contains_snippet_casefold(haystack: str, needle: str) -> bool:
    return normalize_space(needle).casefold() in normalize_space(haystack).casefold()


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
    if not (REPO_ROOT / value).is_file():
        fail(failures, f"{field} path is missing: {value}")
    return value


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    if manifest.get("schema_version") != 1:
        fail(failures, "performance-readiness.json schema_version must be 1")
    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        fail(failures, "description must be a non-empty string")

    for field in (
        "workflow_doc",
        "quality_gates_doc",
        "load_profile",
        "performance_readme",
        "tests_readme",
        "observability_readiness_doc",
        "operations_readiness_doc",
        "mvp_scope_doc",
        "traceability_doc",
        "github_publication_runbook",
    ):
        required_path(manifest, field, failures)

    if not isinstance(manifest.get("required_profile"), dict):
        fail(failures, "required_profile must be an object")

    for field in ("required_doc_phrases",):
        value = manifest.get(field)
        if not isinstance(value, list) or not value:
            fail(failures, f"{field} must be a non-empty list")


def validate_load_profile(manifest: dict[str, Any], failures: list[str]) -> None:
    profile_path = manifest.get("load_profile")
    required = manifest.get("required_profile")
    if not isinstance(profile_path, str) or not isinstance(required, dict):
        return
    profile = load_json(REPO_ROOT / profile_path, failures)
    if not isinstance(profile, dict):
        return

    if profile.get("schema_version") != 1:
        fail(failures, f"{profile_path} schema_version must be 1")
    if profile.get("profile_id") != required.get("profile_id"):
        fail(failures, f"{profile_path} profile_id must be {required.get('profile_id')!r}")
    if profile.get("synthetic_only") is not required.get("synthetic_only"):
        fail(failures, f"{profile_path} synthetic_only must be {required.get('synthetic_only')!r}")

    for phrase in (
        "Do not use customer exports",
        "production logs",
        "production database snapshots",
        "prompt bodies",
    ):
        rules = profile.get("privacy_rules")
        joined_rules = " ".join(item for item in rules if isinstance(item, str)) if isinstance(rules, list) else ""
        if not contains_snippet(joined_rules, phrase):
            fail(failures, f"{profile_path} privacy_rules missing phrase: {phrase}")

    data_profile = profile.get("data_profile")
    expected_minimums = required.get("minimum_data_profile")
    if not isinstance(data_profile, dict):
        fail(failures, f"{profile_path} data_profile must be an object")
    elif isinstance(expected_minimums, dict):
        for key, expected in expected_minimums.items():
            actual = data_profile.get(key)
            if not isinstance(actual, int) or actual < int(expected):
                fail(failures, f"{profile_path} data_profile.{key} must be at least {expected}")

    targets = profile.get("targets")
    if not isinstance(targets, dict):
        fail(failures, f"{profile_path} targets must be an object")
    else:
        for target in string_list(required.get("required_targets"), "required_profile.required_targets", failures):
            value = targets.get(target)
            if not isinstance(value, (int, float)) or value <= 0:
                fail(failures, f"{profile_path} target {target} must be a positive number")

    scenarios = profile.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        fail(failures, f"{profile_path} scenarios must be a non-empty list")
        return

    scenario_by_id: dict[str, dict[str, Any]] = {}
    for index, scenario in enumerate(scenarios, 1):
        if not isinstance(scenario, dict):
            fail(failures, f"{profile_path} scenarios[{index}] must be an object")
            continue
        scenario_id = scenario.get("id")
        if not isinstance(scenario_id, str) or not scenario_id:
            fail(failures, f"{profile_path} scenarios[{index}].id must be a non-empty string")
            continue
        if scenario_id in scenario_by_id:
            fail(failures, f"{profile_path} duplicate scenario id: {scenario_id}")
        scenario_by_id[scenario_id] = scenario
        for field in ("surface", "target"):
            if not isinstance(scenario.get(field), str) or not scenario[field].strip():
                fail(failures, f"{profile_path} {scenario_id}.{field} must be a non-empty string")
        for field in ("roles", "minimum_records", "required_evidence"):
            string_list(scenario.get(field), f"{profile_path}.{scenario_id}.{field}", failures)

    for scenario_id in string_list(
        required.get("required_scenario_ids"),
        "required_profile.required_scenario_ids",
        failures,
    ):
        if scenario_id not in scenario_by_id:
            fail(failures, f"{profile_path} missing scenario id: {scenario_id}")

    evidence_text = " ".join(
        " ".join(item for item in scenario.get("required_evidence", []) if isinstance(item, str))
        for scenario in scenarios
        if isinstance(scenario, dict)
    )
    for term in string_list(
        required.get("required_scenario_evidence_terms"),
        "required_profile.required_scenario_evidence_terms",
        failures,
    ):
        if term.lower() not in evidence_text.lower():
            fail(failures, f"{profile_path} required evidence missing term: {term}")


def validate_docs(manifest: dict[str, Any], failures: list[str]) -> None:
    entries = manifest.get("required_doc_phrases")
    if not isinstance(entries, list):
        return
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            fail(failures, f"required_doc_phrases[{index}] must be an object")
            continue
        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value:
            fail(failures, f"required_doc_phrases[{index}].path must be a non-empty string")
            continue
        text = read_text(REPO_ROOT / path_value, failures)
        for phrase in string_list(entry.get("phrases"), f"required_doc_phrases[{index}].phrases", failures):
            if not contains_snippet_casefold(text, phrase):
                fail(failures, f"{path_value} missing performance-readiness phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    value = load_json(MANIFEST_PATH, failures)
    manifest = value if isinstance(value, dict) else {}

    if manifest:
        validate_shape(manifest, failures)
        validate_load_profile(manifest, failures)
        validate_docs(manifest, failures)

    if failures:
        print("Performance readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Performance readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
