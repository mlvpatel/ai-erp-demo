#!/usr/bin/env python3
"""Validate industry-pack lifecycle rules and docs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "industry-pack-lifecycle.json"


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
        fail(failures, "industry-pack-lifecycle.json schema_version must be 1")

    for field in ("lifecycle_doc", "pack_manifest", "roadmap_doc", "design_template"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            fail(failures, f"{field} must be a non-empty string")
        elif not (REPO_ROOT / value).is_file():
            fail(failures, f"{field} path is missing: {value}")

    status_flow = string_list(manifest.get("status_flow"), "status_flow", failures)
    if status_flow != ["planned", "reserved", "implemented"]:
        fail(failures, "status_flow must be planned, reserved, implemented")

    allowed_entry_gates = set(string_list(manifest.get("allowed_entry_gates"), "allowed_entry_gates", failures))
    required_entry_gates = {"not_started", "discovery_brief_ready", "passed_for_mvp"}
    if not required_entry_gates.issubset(allowed_entry_gates):
        fail(failures, "allowed_entry_gates must include not_started, discovery_brief_ready, passed_for_mvp")

    rules = manifest.get("status_rules")
    if not isinstance(rules, dict):
        fail(failures, "status_rules must be an object")
        return
    for status in ("planned", "reserved", "implemented"):
        rule = rules.get(status)
        if not isinstance(rule, dict):
            fail(failures, f"status_rules.{status} must be an object")
            continue
        string_list(rule.get("allowed_entry_gates"), f"status_rules.{status}.allowed_entry_gates", failures)

    for field in (
        "required_lifecycle_doc_phrases",
        "required_roadmap_phrases",
        "required_template_phrases",
    ):
        string_list(manifest.get(field), field, failures)


def validate_doc_phrases(manifest: dict[str, Any], failures: list[str]) -> None:
    doc_checks = (
        ("lifecycle_doc", "required_lifecycle_doc_phrases"),
        ("roadmap_doc", "required_roadmap_phrases"),
        ("design_template", "required_template_phrases"),
    )
    for path_field, phrase_field in doc_checks:
        path_value = manifest.get(path_field)
        if not isinstance(path_value, str):
            continue
        text = read_text(REPO_ROOT / path_value, failures)
        for phrase in string_list(manifest.get(phrase_field), phrase_field, failures):
            if not contains_snippet(text, phrase):
                fail(failures, f"{path_value}: missing lifecycle phrase: {phrase}")


def pack_docs_exist(pack_id: str, pack: dict[str, Any], failures: list[str]) -> None:
    docs = pack.get("docs")
    if not isinstance(docs, list) or not docs:
        fail(failures, f"{pack_id}: docs must be a non-empty list")
        return
    for doc in docs:
        if not isinstance(doc, str) or not doc.strip():
            fail(failures, f"{pack_id}: docs entries must be non-empty strings")
        elif not (REPO_ROOT / doc).exists():
            fail(failures, f"{pack_id}: doc path is missing: {doc}")


def validate_planned_pack(pack_id: str, pack: dict[str, Any], rule: dict[str, Any], failures: list[str]) -> None:
    if pack.get("app_path") is not None:
        fail(failures, f"{pack_id}: planned packs must leave app_path as null")
    phrase = rule.get("required_verification_phrase")
    verification = pack.get("verification")
    if isinstance(phrase, str):
        if not isinstance(verification, list) or phrase not in verification:
            fail(failures, f"{pack_id}: planned pack verification must include {phrase!r}")


def validate_reserved_pack(pack_id: str, pack: dict[str, Any], rule: dict[str, Any], failures: list[str]) -> None:
    app_path_value = pack.get("app_path")
    if not isinstance(app_path_value, str) or not app_path_value.strip():
        fail(failures, f"{pack_id}: reserved packs must set app_path")
        return

    app_path = REPO_ROOT / app_path_value
    if not app_path.is_dir():
        fail(failures, f"{pack_id}: reserved app_path is not a directory: {app_path_value}")
        return

    readme = app_path / "README.md"
    readme_text = read_text(readme, failures)
    for phrase in string_list(rule.get("required_readme_phrases"), "reserved.required_readme_phrases", failures):
        if not contains_snippet(readme_text, phrase):
            fail(failures, f"{pack_id}: reserved README missing phrase: {phrase}")

    markers = string_list(rule.get("forbidden_generated_markers"), "reserved.forbidden_generated_markers", failures)
    for marker in markers:
        matches = [path for path in app_path.rglob("*") if path.name == marker or marker in path.parts]
        for match in matches:
            fail(failures, f"{pack_id}: reserved pack contains generated marker: {rel(match)}")


def validate_implemented_pack(pack_id: str, pack: dict[str, Any], rule: dict[str, Any], failures: list[str]) -> None:
    app_path_value = pack.get("app_path")
    if not isinstance(app_path_value, str) or not (REPO_ROOT / app_path_value).is_dir():
        fail(failures, f"{pack_id}: implemented packs must set an existing app_path")

    verification = pack.get("verification")
    prefix = rule.get("required_verification_prefix")
    if isinstance(prefix, str):
        if not isinstance(verification, list) or not any(isinstance(item, str) and item.startswith(prefix) for item in verification):
            fail(failures, f"{pack_id}: implemented pack verification must include a {prefix!r} command")

    doc_phrase = rule.get("required_doc_phrase")
    if isinstance(doc_phrase, str):
        combined_doc_text = ""
        docs = pack.get("docs", [])
        if isinstance(docs, list):
            combined_doc_text = "\n".join(
                read_text(REPO_ROOT / doc, failures)
                for doc in docs
                if isinstance(doc, str)
            )
        if not contains_snippet(combined_doc_text, doc_phrase):
            fail(failures, f"{pack_id}: implemented pack docs must mention {doc_phrase!r}")


def validate_pack_statuses(manifest: dict[str, Any], failures: list[str]) -> None:
    pack_manifest_path = manifest.get("pack_manifest")
    if not isinstance(pack_manifest_path, str):
        return
    pack_manifest = load_json(REPO_ROOT / pack_manifest_path, failures)
    packs = pack_manifest.get("packs")
    if not isinstance(packs, list) or not packs:
        fail(failures, f"{pack_manifest_path}: packs must be a non-empty list")
        return

    rules = manifest.get("status_rules", {})
    allowed_statuses = set(string_list(manifest.get("status_flow"), "status_flow", failures))
    allowed_entry_gates = set(string_list(manifest.get("allowed_entry_gates"), "allowed_entry_gates", failures))

    implemented_count = 0
    reserved_or_planned_count = 0
    for index, pack in enumerate(packs, 1):
        if not isinstance(pack, dict):
            fail(failures, f"{pack_manifest_path}: packs[{index}] must be an object")
            continue
        pack_id = pack.get("id") if isinstance(pack.get("id"), str) else f"packs[{index}]"
        status = pack.get("status")
        if status not in allowed_statuses:
            fail(failures, f"{pack_id}: unsupported lifecycle status {status!r}")
            continue

        entry_gate = pack.get("entry_gate")
        if entry_gate not in allowed_entry_gates:
            fail(failures, f"{pack_id}: unsupported entry_gate {entry_gate!r}")

        rule = rules.get(status)
        if isinstance(rule, dict):
            status_entry_gates = set(string_list(rule.get("allowed_entry_gates"), f"status_rules.{status}.allowed_entry_gates", failures))
            if entry_gate not in status_entry_gates:
                fail(failures, f"{pack_id}: entry_gate {entry_gate!r} is not allowed for status {status!r}")

        pack_docs_exist(pack_id, pack, failures)
        if status == "planned" and isinstance(rule, dict):
            reserved_or_planned_count += 1
            validate_planned_pack(pack_id, pack, rule, failures)
        elif status == "reserved" and isinstance(rule, dict):
            reserved_or_planned_count += 1
            validate_reserved_pack(pack_id, pack, rule, failures)
        elif status == "implemented" and isinstance(rule, dict):
            implemented_count += 1
            validate_implemented_pack(pack_id, pack, rule, failures)

    if implemented_count < 1:
        fail(failures, "industry lifecycle requires at least one implemented pack")
    if reserved_or_planned_count < 1:
        fail(failures, "industry lifecycle requires at least one future pack")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_doc_phrases(manifest, failures)
        validate_pack_statuses(manifest, failures)

    if failures:
        print("Industry pack lifecycle check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Industry pack lifecycle check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
