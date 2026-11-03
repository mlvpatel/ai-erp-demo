#!/usr/bin/env python3
"""Validate industry-pack lifecycle rules and docs."""

from __future__ import annotations

from typing import Any

from _gate import REPO_ROOT, contains_snippet, load_json, read_text, rel, report, string_list


MANIFEST_PATH = REPO_ROOT / "config" / "industry-pack-lifecycle.json"
REQUIRED_PACK_FIELDS = {
    "id",
    "title",
    "status",
    "app_path",
    "docs",
    "entry_gate",
    "first_proof_workflow",
    "erpnext_reuse",
    "ai_allowed",
    "ai_forbidden",
    "verification",
}
REQUIRED_AI_FORBIDDEN_TERMS = ("financial", "inventory", "payroll", "permission", "compliance")


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    for field in ("lifecycle_doc", "pack_manifest", "roadmap_doc", "design_template"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{field} must be a non-empty string")
        elif not (REPO_ROOT / value).is_file():
            failures.append(f"{field} path is missing: {value}")

    rules = manifest.get("status_rules")
    if not isinstance(rules, dict):
        failures.append("status_rules must be an object")
        return
    if list(rules) != ["planned", "reserved", "configured_demo", "implemented"]:
        failures.append("status_rules must list planned, reserved, configured_demo, implemented in that order")
    for status in ("planned", "reserved", "configured_demo", "implemented"):
        rule = rules.get(status)
        if not isinstance(rule, dict):
            failures.append(f"status_rules.{status} must be an object")
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
                failures.append(f"{path_value}: missing lifecycle phrase: {phrase}")


def pack_docs_exist(pack_id: str, pack: dict[str, Any], failures: list[str]) -> None:
    docs = pack.get("docs")
    if not isinstance(docs, list) or not docs:
        failures.append(f"{pack_id}: docs must be a non-empty list")
        return
    for doc in docs:
        if not isinstance(doc, str) or not doc.strip():
            failures.append(f"{pack_id}: docs entries must be non-empty strings")
        elif not (REPO_ROOT / doc).exists():
            failures.append(f"{pack_id}: doc path is missing: {doc}")


def validate_planned_pack(pack_id: str, pack: dict[str, Any], rule: dict[str, Any], failures: list[str]) -> None:
    if pack.get("app_path") is not None:
        failures.append(f"{pack_id}: planned packs must leave app_path as null")
    phrase = rule.get("required_verification_phrase")
    verification = pack.get("verification")
    if isinstance(phrase, str):
        if not isinstance(verification, list) or phrase not in verification:
            failures.append(f"{pack_id}: planned pack verification must include {phrase!r}")


def validate_reserved_pack(
    pack_id: str, pack: dict[str, Any], rule: dict[str, Any], markers: list[str], failures: list[str]
) -> None:
    app_path_value = pack.get("app_path")
    if not isinstance(app_path_value, str) or not app_path_value.strip():
        failures.append(f"{pack_id}: reserved packs must set app_path")
        return

    app_path = REPO_ROOT / app_path_value
    if not app_path.is_dir():
        failures.append(f"{pack_id}: reserved app_path is not a directory: {app_path_value}")
        return

    readme = app_path / "README.md"
    readme_text = read_text(readme, failures)
    for phrase in string_list(rule.get("required_readme_phrases"), "reserved.required_readme_phrases", failures):
        if not contains_snippet(readme_text, phrase):
            failures.append(f"{pack_id}: reserved README missing phrase: {phrase}")

    for marker in markers:
        matches = [path for path in app_path.rglob("*") if path.name == marker or marker in path.parts]
        for match in matches:
            failures.append(f"{pack_id}: reserved pack contains generated marker: {rel(match)}")

    docs = pack.get("docs")
    discovery_docs = [
        doc
        for doc in docs
        if isinstance(doc, str) and doc.startswith("docs/discovery/")
    ] if isinstance(docs, list) else []
    if len(discovery_docs) != 1:
        failures.append(f"{pack_id}: reserved pack requires exactly one docs/discovery brief")
        return

    evidence_level = pack.get("discovery_evidence_level")
    human_validation = pack.get("human_validation")
    if pack.get("entry_gate") == "not_started":
        if evidence_level != "hypothesis_only" or human_validation != "pending":
            failures.append(
                f"{pack_id}: not_started must remain hypothesis_only with human validation pending",
            )
        brief_text = read_text(REPO_ROOT / discovery_docs[0], failures)
        phrases = string_list(
            rule.get("hypothesis_required_phrases"),
            "reserved.hypothesis_required_phrases",
            failures,
        )
        for phrase in phrases:
            if not contains_snippet(brief_text, phrase):
                failures.append(f"{pack_id}: hypothesis brief missing phrase: {phrase}")
    elif pack.get("entry_gate") == "discovery_brief_ready":
        if evidence_level == "hypothesis_only" or human_validation != "approved":
            failures.append(f"{pack_id}: discovery_brief_ready requires approved human evidence")


def validate_documentation_only_app(
    pack_id: str, pack: dict[str, Any], rule: dict[str, Any], markers: list[str], failures: list[str]
) -> None:
    app_path_value = pack.get("app_path")
    if not isinstance(app_path_value, str) or not app_path_value.strip():
        failures.append(f"{pack_id}: documentation-only pack must set app_path")
        return
    app_path = REPO_ROOT / app_path_value
    if not app_path.is_dir():
        failures.append(f"{pack_id}: app_path is not a directory: {app_path_value}")
        return
    readme_text = read_text(app_path / "README.md", failures)
    for phrase in string_list(rule.get("required_readme_phrases"), f"{pack_id}.required_readme_phrases", failures):
        if not contains_snippet(readme_text, phrase):
            failures.append(f"{pack_id}: README missing configured-demo phrase: {phrase}")
    for marker in markers:
        for match in [path for path in app_path.rglob("*") if path.name == marker or marker in path.parts]:
            failures.append(f"{pack_id}: configured demo contains generated marker: {rel(match)}")


def validate_configured_demo(
    pack_id: str, pack: dict[str, Any], rule: dict[str, Any], markers: list[str], failures: list[str]
) -> None:
    validate_documentation_only_app(pack_id, pack, rule, markers, failures)
    if pack.get("entry_gate") != "configured_demo_ready":
        failures.append(f"{pack_id}: configured_demo must use configured_demo_ready entry gate")
    if pack.get("discovery_evidence_level") != "hypothesis_only" or pack.get("human_validation") != "pending":
        failures.append(f"{pack_id}: configured demo must keep product evidence hypothesis_only and human validation pending")

    docs = pack.get("docs", [])
    discovery_docs = [doc for doc in docs if isinstance(doc, str) and doc.startswith("docs/discovery/")]
    runbooks = [doc for doc in docs if isinstance(doc, str) and doc.startswith("docs/runbooks/")]
    if len(discovery_docs) != 1:
        failures.append(f"{pack_id}: configured demo requires exactly one discovery brief")
    else:
        discovery_text = read_text(REPO_ROOT / discovery_docs[0], failures)
        for phrase in string_list(rule.get("required_discovery_phrases"), "configured_demo.required_discovery_phrases", failures):
            if not contains_snippet(discovery_text, phrase):
                failures.append(f"{pack_id}: discovery brief missing configured-demo phrase: {phrase}")
    if len(runbooks) != 1:
        failures.append(f"{pack_id}: configured demo requires exactly one walkthrough runbook")

    demo_manifest_path = pack.get("demo_manifest")
    if not isinstance(demo_manifest_path, str) or not demo_manifest_path.startswith("config/industry-demo-"):
        failures.append(f"{pack_id}: demo_manifest must use config/industry-demo-* path")
        return
    demo = load_json(REPO_ROOT / demo_manifest_path, failures)
    if demo.get("pack_id") != pack_id:
        failures.append(f"{pack_id}: demo manifest pack_id mismatch")
    if demo.get("status") != "configured_demo" or demo.get("synthetic_only") is not True:
        failures.append(f"{pack_id}: demo manifest must be configured_demo and synthetic_only")
    string_list(demo.get("invariants"), f"{pack_id}.demo.invariants", failures)
    for action in ("seeder", "reset"):
        value = demo.get(action)
        if not isinstance(value, dict):
            failures.append(f"{pack_id}: demo {action} must be an object")
            continue
        path_value = value.get("path")
        if not isinstance(path_value, str) or not (REPO_ROOT / path_value).is_file():
            failures.append(f"{pack_id}: demo {action} path is missing")
        if not isinstance(value.get("function"), str) or not value.get("function"):
            failures.append(f"{pack_id}: demo {action} function is required")
        if value.get("argument") != pack_id:
            failures.append(f"{pack_id}: demo {action} argument must match pack id")
    seeder = demo.get("seeder")
    seeder_path = seeder.get("path") if isinstance(seeder, dict) else None
    if isinstance(seeder_path, str) and (REPO_ROOT / seeder_path).is_file():
        seeder_text = read_text(REPO_ROOT / seeder_path, failures)
        for phrase in string_list(rule.get("required_seeder_phrases"), "configured_demo.required_seeder_phrases", failures):
            if phrase not in seeder_text:
                failures.append(f"{pack_id}: configured-demo seeder missing safety phrase: {phrase}")
        for phrase in string_list(rule.get("forbidden_seeder_phrases"), "configured_demo.forbidden_seeder_phrases", failures):
            if phrase in seeder_text:
                failures.append(f"{pack_id}: configured-demo seeder contains forbidden posting phrase: {phrase}")
    invariant_text = " ".join(demo.get("invariants", [])).casefold() if isinstance(demo.get("invariants"), list) else ""
    for phrase in ("does not submit", "no ai route", "human validation remains pending"):
        if phrase not in invariant_text:
            failures.append(f"{pack_id}: demo invariants must state {phrase!r}")


def validate_implemented_pack(pack_id: str, pack: dict[str, Any], rule: dict[str, Any], failures: list[str]) -> None:
    app_path_value = pack.get("app_path")
    if not isinstance(app_path_value, str) or not (REPO_ROOT / app_path_value / "README.md").is_file():
        failures.append(f"{pack_id}: implemented packs must set an existing app_path with README.md")

    verification = pack.get("verification")
    prefix = rule.get("required_verification_prefix")
    if isinstance(prefix, str):
        if not isinstance(verification, list) or not any(isinstance(item, str) and item.startswith(prefix) for item in verification):
            failures.append(f"{pack_id}: implemented pack verification must include a {prefix!r} command")

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
            failures.append(f"{pack_id}: implemented pack docs must mention {doc_phrase!r}")


def validate_pack_statuses(manifest: dict[str, Any], failures: list[str]) -> None:
    pack_manifest_path = manifest.get("pack_manifest")
    if not isinstance(pack_manifest_path, str):
        return
    pack_manifest = load_json(REPO_ROOT / pack_manifest_path, failures)
    packs = pack_manifest.get("packs")
    if not isinstance(packs, list) or not packs:
        failures.append(f"{pack_manifest_path}: packs must be a non-empty list")
        return

    rules = manifest.get("status_rules")
    if not isinstance(rules, dict):
        return
    allowed_statuses = set(rules)
    markers = string_list(manifest.get("forbidden_generated_markers"), "forbidden_generated_markers", failures)

    implemented_count = 0
    reserved_or_planned_count = 0
    seen_ids: set[str] = set()
    for index, pack in enumerate(packs, 1):
        if not isinstance(pack, dict):
            failures.append(f"{pack_manifest_path}: packs[{index}] must be an object")
            continue
        pack_id = pack.get("id")
        if not isinstance(pack_id, str) or not pack_id.strip():
            failures.append(f"{pack_manifest_path}: packs[{index}].id must be a non-empty string")
            pack_id = f"packs[{index}]"
        elif pack_id in seen_ids:
            failures.append(f"{pack_id}: duplicate pack id")
        seen_ids.add(pack_id)
        missing = sorted(REQUIRED_PACK_FIELDS - set(pack))
        if missing:
            failures.append(f"{pack_id}: missing required fields: {', '.join(missing)}")
        for field in ("title", "first_proof_workflow"):
            if not isinstance(pack.get(field), str) or not pack[field].strip():
                failures.append(f"{pack_id}: {field} must be a non-empty string")
        for field in ("erpnext_reuse", "ai_allowed", "verification"):
            string_list(pack.get(field), f"{pack_id}.{field}", failures)
        forbidden_text = " ".join(string_list(pack.get("ai_forbidden"), f"{pack_id}.ai_forbidden", failures)).lower()
        for term in REQUIRED_AI_FORBIDDEN_TERMS:
            if term not in forbidden_text:
                failures.append(f"{pack_id}: ai_forbidden must mention {term}")

        status = pack.get("status")
        if status not in allowed_statuses:
            failures.append(f"{pack_id}: unsupported lifecycle status {status!r}")
            continue

        entry_gate = pack.get("entry_gate")
        rule = rules.get(status)
        if isinstance(rule, dict):
            status_entry_gates = set(string_list(rule.get("allowed_entry_gates"), f"status_rules.{status}.allowed_entry_gates", failures))
            if entry_gate not in status_entry_gates:
                failures.append(f"{pack_id}: entry_gate {entry_gate!r} is not allowed for status {status!r}")

        pack_docs_exist(pack_id, pack, failures)
        if status == "planned" and isinstance(rule, dict):
            reserved_or_planned_count += 1
            validate_planned_pack(pack_id, pack, rule, failures)
        elif status == "reserved" and isinstance(rule, dict):
            reserved_or_planned_count += 1
            validate_reserved_pack(pack_id, pack, rule, markers, failures)
        elif status == "configured_demo" and isinstance(rule, dict):
            reserved_or_planned_count += 1
            validate_configured_demo(pack_id, pack, rule, markers, failures)
        elif status == "implemented" and isinstance(rule, dict):
            implemented_count += 1
            validate_implemented_pack(pack_id, pack, rule, failures)

    if implemented_count < 1:
        failures.append("industry lifecycle requires at least one implemented pack")
    if reserved_or_planned_count < 1:
        failures.append("industry lifecycle requires at least one future pack")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_doc_phrases(manifest, failures)
        validate_pack_statuses(manifest, failures)

    return report("Industry pack lifecycle check", failures)


if __name__ == "__main__":
    raise SystemExit(main())
