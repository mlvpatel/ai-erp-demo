#!/usr/bin/env python3
"""Validate the field-service 9/10 target scorecard."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "field-service-9-scorecard.json"
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMPLEMENTATION_STATES = {"planned", "partly_implemented", "implemented"}
REQUIRED_FEATURE_IDS = {
    "verifiable-evidence-to-cash-ledger",
    "cannot-close-recovery-coach",
    "margin-leakage-guardian",
    "provenance-based-repair-memory",
    "safe-agent-replay",
    "bounded-scheduling-optimizer",
    "mobile-field-execution",
    "governed-demo-to-pilot-release",
}
FORBIDDEN_CLAIMS = (
    "production ready",
    "human uat approved",
    "gdpr compliant",
    "full multi-industry erp",
    "a 9/10 product",
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"missing JSON file: {rel(path)}")
        return {}
    except json.JSONDecodeError as exc:
        failures.append(f"invalid JSON in {rel(path)}: {exc}")
        return {}

    if not isinstance(value, dict):
        failures.append(f"{rel(path)} must contain a JSON object")
        return {}
    return value


def require_text(value: Any, field: str, failures: list[str], min_len: int = 30) -> None:
    if not isinstance(value, str) or len(value.strip()) < min_len:
        failures.append(f"{field} must be descriptive text")


def require_path(path_value: Any, owner: str, failures: list[str]) -> None:
    if not isinstance(path_value, str) or not path_value.strip():
        failures.append(f"{owner}: path must be a non-empty string")
        return
    if not (REPO_ROOT / path_value).exists():
        failures.append(f"{owner}: path does not exist: {path_value}")


def validate_requirements_status(value: Any, failures: list[str]) -> None:
    if not isinstance(value, dict):
        failures.append("requirements_status must be an object")
        return

    for status in ("verified", "assumed", "deferred"):
        entries = value.get(status)
        if not isinstance(entries, list) or not entries:
            failures.append(f"requirements_status.{status} must be a non-empty list")
            continue
        for index, entry in enumerate(entries, 1):
            require_text(entry, f"requirements_status.{status}[{index}]", failures, min_len=20)


def validate_system_records(value: Any, failures: list[str]) -> None:
    if not isinstance(value, list) or len(value) < 3:
        failures.append("system_records must list ERPNext, service app, and AI records")
        return

    for index, record in enumerate(value, 1):
        if not isinstance(record, dict):
            failures.append(f"system_records[{index}] must be an object")
            continue
        for field in ("entity", "integration_owner"):
            require_text(record.get(field), f"system_records[{index}].{field}", failures, min_len=10)
        require_text(record.get("system_of_record"), f"system_records[{index}].system_of_record", failures, min_len=3)


def validate_feature(feature: Any, index: int, seen_ids: set[str], failures: list[str]) -> tuple[float, float] | None:
    if not isinstance(feature, dict):
        failures.append(f"features[{index}] must be an object")
        return None

    feature_id = feature.get("id")
    if not isinstance(feature_id, str) or not ID_PATTERN.match(feature_id):
        failures.append(f"features[{index}].id must be kebab-case")
        feature_id = f"features[{index}]"
    elif feature_id in seen_ids:
        failures.append(f"{feature_id}: duplicate feature id")
    else:
        seen_ids.add(feature_id)

    if feature.get("implementation_state") not in IMPLEMENTATION_STATES:
        failures.append(
            f"{feature_id}: implementation_state must be one of {', '.join(sorted(IMPLEMENTATION_STATES))}",
        )

    current_score = feature.get("current_score")
    target_score = feature.get("target_score")
    if not isinstance(current_score, (int, float)) or not 0 <= current_score <= 10:
        failures.append(f"{feature_id}: current_score must be between 0 and 10")
        current_score = None
    if not isinstance(target_score, (int, float)) or not 0 <= target_score <= 10:
        failures.append(f"{feature_id}: target_score must be between 0 and 10")
        target_score = None

    if isinstance(current_score, (int, float)) and isinstance(target_score, (int, float)):
        if current_score >= target_score:
            failures.append(f"{feature_id}: current_score must remain below target_score until evidence exists")
        if target_score < 9:
            failures.append(f"{feature_id}: target_score must be at least 9 for the 9/10 program")

    required_text_fields = {
        "title": 5,
        "role_owner": 5,
        "input": 20,
        "output": 20,
        "decision_logic": 20,
        "validation_gate": 20,
        "feedback_loop": 20,
        "failure_handling": 20,
        "optimization_step": 20,
        "scalability_note": 20,
    }
    for field, min_len in required_text_fields.items():
        require_text(feature.get(field), f"{feature_id}.{field}", failures, min_len=min_len)

    evidence_paths = feature.get("evidence_paths")
    if not isinstance(evidence_paths, list) or not evidence_paths:
        failures.append(f"{feature_id}: evidence_paths must be a non-empty list")
    else:
        for path in evidence_paths:
            require_path(path, feature_id, failures)

    if isinstance(current_score, (int, float)) and isinstance(target_score, (int, float)):
        return float(current_score), float(target_score)
    return None


def validate_claim_boundaries(source_paths: list[str], failures: list[str]) -> None:
    combined = ""
    for path_value in source_paths:
        path = REPO_ROOT / path_value
        if path.is_file():
            combined += "\n" + path.read_text(encoding="utf-8").lower()

    for claim in FORBIDDEN_CLAIMS:
        if claim not in combined:
            failures.append(f"source docs must explicitly forbid claiming {claim!r}")


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)


    source_docs = manifest.get("source_docs")
    if not isinstance(source_docs, list) or not source_docs:
        failures.append("source_docs must be a non-empty list")
        source_docs = []
    else:
        for path in source_docs:
            require_path(path, "source_docs", failures)

    for field in (
        "target_category",
        "claim_boundary",
        "target_user",
        "business_outcome",
        "measurable_success_signal",
    ):
        require_text(manifest.get(field), field, failures)
    require_text(manifest.get("process_owner"), "process_owner", failures, min_len=5)

    validate_requirements_status(manifest.get("requirements_status"), failures)
    validate_system_records(manifest.get("system_records"), failures)

    features = manifest.get("features")
    score_pairs: list[tuple[float, float]] = []
    if not isinstance(features, list) or not features:
        failures.append("features must be a non-empty list")
    else:
        seen_ids: set[str] = set()
        for index, feature in enumerate(features, 1):
            pair = validate_feature(feature, index, seen_ids, failures)
            if pair:
                score_pairs.append(pair)

        missing = REQUIRED_FEATURE_IDS - seen_ids
        if missing:
            failures.append(f"missing required feature ids: {', '.join(sorted(missing))}")

    if score_pairs and round(sum(pair[0] for pair in score_pairs) / len(score_pairs), 1) >= 9:
        failures.append("average feature current_score must stay below 9 until validated evidence exists")

    validate_claim_boundaries([path for path in source_docs if isinstance(path, str)], failures)

    if failures:
        print("Field-service 9/10 scorecard check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Field-service 9/10 scorecard check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
