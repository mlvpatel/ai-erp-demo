#!/usr/bin/env python3
"""Validate transaction-safety invariants for the MVP ERP workflow."""

from __future__ import annotations

import sys
from typing import Any

from _gate import REPO_ROOT, contains_snippet, load_json, load_json_object, read_text


MANIFEST_PATH = REPO_ROOT / "config" / "transaction-safety.json"


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


def acceptance_claim_ids(manifest: dict[str, Any], failures: list[str]) -> set[str]:
    path_value = manifest.get("mvp_acceptance")
    if not isinstance(path_value, str):
        return set()
    value = load_json_object(REPO_ROOT / path_value, failures)
    if not isinstance(value, dict):
        return set()
    claims = value.get("claims")
    if not isinstance(claims, list):
        failures.append(f"{path_value}: claims must be a list")
        return set()
    return {
        claim["id"]
        for claim in claims
        if isinstance(claim, dict) and isinstance(claim.get("id"), str)
    }


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


def validate_docs(manifest: dict[str, Any], failures: list[str]) -> None:
    doc_text = "\n".join(
        read_text(REPO_ROOT / path_value, failures)
        for path_value in (manifest.get("workflow_doc"), manifest.get("service_workflow_doc"))
        if isinstance(path_value, str)
    )
    for phrase in string_list(manifest.get("required_doc_phrases"), "required_doc_phrases", failures):
        if not contains_snippet(doc_text, phrase):
            failures.append(f"transaction safety docs missing phrase: {phrase}")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_invariants(manifest, failures)
        validate_docs(manifest, failures)

    if failures:
        print("Transaction safety check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Transaction safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
