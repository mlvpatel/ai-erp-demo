#!/usr/bin/env python3
"""Validate transaction-safety invariants for the MVP ERP workflow."""

from __future__ import annotations

from typing import Any

from _gate import (
    REPO_ROOT,
    acceptance_claim_ids,
    contains_snippet,
    joined_doc_phrases,
    load_json,
    read_text,
    report,
    string_list,
)


MANIFEST_PATH = REPO_ROOT / "config" / "transaction-safety.json"
DOC_FIELDS = ("workflow_doc", "service_workflow_doc")


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    for field in (
        "workflow_doc",
        "service_workflow_doc",
        "mvp_acceptance",
        "service_work_order_controller",
        "service_work_order_tests",
        "ai_proposal_controller",
    ):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{field} must be a non-empty string")
        elif not (REPO_ROOT / value).is_file():
            failures.append(f"{field} path is missing: {value}")

    invariants = manifest.get("invariants")
    if not isinstance(invariants, list) or not invariants:
        failures.append("invariants must be a non-empty list")
        return
    seen_ids: set[str] = set()
    for index, invariant in enumerate(invariants, 1):
        if not isinstance(invariant, dict):
            failures.append(f"invariants[{index}] must be an object")
            continue
        invariant_id = invariant.get("id")
        if not isinstance(invariant_id, str) or not invariant_id:
            failures.append(f"invariants[{index}].id must be a non-empty string")
        elif invariant_id in seen_ids:
            failures.append(f"{invariant_id}: duplicate invariant id")
        else:
            seen_ids.add(invariant_id)
        if not isinstance(invariant.get("description"), str) or not invariant["description"].strip():
            failures.append(f"{invariant_id}: description must be non-empty")
        string_list(invariant.get("code_snippets"), f"{invariant_id}.code_snippets", failures)
        string_list(invariant.get("test_anchors"), f"{invariant_id}.test_anchors", failures)

    string_list(manifest.get("required_doc_phrases"), "required_doc_phrases", failures)


def validate_invariants(manifest: dict[str, Any], failures: list[str]) -> None:
    source_paths = [
        manifest.get("service_work_order_controller"),
        manifest.get("service_work_order_tests"),
        manifest.get("ai_proposal_controller"),
    ]
    source_text = "\n".join(
        read_text(REPO_ROOT / path_value, failures)
        for path_value in source_paths
        if isinstance(path_value, str)
    )
    test_text = (
        read_text(REPO_ROOT / manifest["service_work_order_tests"], failures)
        if isinstance(manifest.get("service_work_order_tests"), str)
        else ""
    )
    claim_ids = acceptance_claim_ids(manifest, failures)

    for invariant in manifest.get("invariants", []):
        if not isinstance(invariant, dict):
            continue
        invariant_id = str(invariant.get("id", "<missing-id>"))
        for snippet in string_list(invariant.get("code_snippets"), f"{invariant_id}.code_snippets", failures):
            if not contains_snippet(source_text, snippet):
                failures.append(f"{invariant_id}: missing code snippet: {snippet}")
        for anchor in string_list(invariant.get("test_anchors"), f"{invariant_id}.test_anchors", failures):
            if not contains_snippet(test_text, anchor):
                failures.append(f"{invariant_id}: missing test anchor: {anchor}")
        claim_id = invariant.get("acceptance_claim")
        if isinstance(claim_id, str) and claim_id not in claim_ids:
            failures.append(f"{invariant_id}: acceptance claim is not in config/mvp-acceptance.json: {claim_id}")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_invariants(manifest, failures)
        joined_doc_phrases(manifest, DOC_FIELDS, "transaction safety", failures)

    return report("Transaction safety check", failures)


if __name__ == "__main__":
    raise SystemExit(main())
