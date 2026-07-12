#!/usr/bin/env python3
"""Validate MVP acceptance claims against source docs and evidence anchors."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "mvp-acceptance.json"
DEV_HELPER = REPO_ROOT / "scripts" / "dev.sh"

ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VALID_STATUS = {"implemented", "prepared"}


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


def source_acceptance_metrics(path: Path, section_name: str, failures: list[str]) -> list[str]:
    if not path.is_file():
        fail(failures, f"source_doc does not exist: {rel(path)}")
        return []

    metrics: list[str] = []
    current_metric: list[str] = []
    in_section = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if in_section and current_metric:
                metrics.append(" ".join(current_metric))
                current_metric = []
            in_section = line[3:].strip() == section_name
            continue
        if in_section and line.startswith("#"):
            if current_metric:
                metrics.append(" ".join(current_metric))
            break
        if in_section and line.startswith("- "):
            if current_metric:
                metrics.append(" ".join(current_metric))
            current_metric = [line[2:].strip()]
        elif in_section and current_metric and line.startswith("  "):
            current_metric.append(line.strip())

    if in_section and current_metric:
        metrics.append(" ".join(current_metric))

    if not metrics:
        fail(failures, f"{rel(path)} has no bullet metrics in section {section_name!r}")
    return metrics


def dev_helper_commands() -> set[str]:
    if not DEV_HELPER.is_file():
        return set()
    text = DEV_HELPER.read_text(encoding="utf-8")
    return set(re.findall(r"^\s{2}([a-z][a-z0-9-]*)\s", text, flags=re.MULTILINE))


def validate_command(claim_id: str, command: Any, allowed_dev_commands: set[str], failures: list[str]) -> None:
    if not isinstance(command, str) or not command.strip():
        fail(failures, f"{claim_id}: verification command must be a non-empty string")
        return

    parts = command.split()
    if len(parts) != 2 or parts[0] != "scripts/dev.sh":
        fail(failures, f"{claim_id}: command must use scripts/dev.sh <command>: {command}")
        return

    if parts[1] not in allowed_dev_commands:
        fail(failures, f"{claim_id}: scripts/dev.sh command is not documented in helper usage: {parts[1]}")


def validate_anchor(claim_id: str, anchor: Any, failures: list[str]) -> None:
    if not isinstance(anchor, dict):
        fail(failures, f"{claim_id}: each anchor must be an object")
        return

    path_value = anchor.get("path")
    contains = anchor.get("contains")
    if not isinstance(path_value, str) or not path_value.strip():
        fail(failures, f"{claim_id}: anchor path must be non-empty")
        return
    if not isinstance(contains, str) or not contains:
        fail(failures, f"{claim_id}: anchor contains must be non-empty")
        return

    path = REPO_ROOT / path_value
    if not path.is_file():
        fail(failures, f"{claim_id}: anchor path does not exist: {path_value}")
        return

    text = path.read_text(encoding="utf-8")
    if contains not in text:
        fail(failures, f"{claim_id}: anchor text not found in {path_value}: {contains!r}")


def validate_claim(
    claim: Any,
    index: int,
    allowed_dev_commands: set[str],
    seen_ids: set[str],
    failures: list[str],
) -> str | None:
    if not isinstance(claim, dict):
        fail(failures, f"claims[{index}] must be an object")
        return None

    claim_id = claim.get("id")
    if not isinstance(claim_id, str) or not ID_PATTERN.match(claim_id):
        fail(failures, f"claims[{index}].id must be kebab-case")
        claim_id = f"claims[{index}]"
    elif claim_id in seen_ids:
        fail(failures, f"{claim_id}: duplicate claim id")
    else:
        seen_ids.add(claim_id)

    source_metric = claim.get("source_metric")
    if not isinstance(source_metric, str) or not source_metric.strip():
        fail(failures, f"{claim_id}: source_metric must be non-empty")
        source_metric = None

    if claim.get("status") not in VALID_STATUS:
        fail(failures, f"{claim_id}: status must be one of {', '.join(sorted(VALID_STATUS))}")

    safety_boundary = claim.get("safety_boundary")
    if not isinstance(safety_boundary, str) or len(safety_boundary.strip()) < 30:
        fail(failures, f"{claim_id}: safety_boundary must describe the guarded behavior")

    evidence_paths = claim.get("evidence_paths")
    if not isinstance(evidence_paths, list) or not evidence_paths:
        fail(failures, f"{claim_id}: evidence_paths must be a non-empty list")
    else:
        for evidence_path in evidence_paths:
            if not isinstance(evidence_path, str):
                fail(failures, f"{claim_id}: every evidence path must be a string")
            elif not (REPO_ROOT / evidence_path).exists():
                fail(failures, f"{claim_id}: evidence path does not exist: {evidence_path}")

    anchors = claim.get("anchors")
    if not isinstance(anchors, list) or not anchors:
        fail(failures, f"{claim_id}: anchors must be a non-empty list")
    else:
        for anchor in anchors:
            validate_anchor(claim_id, anchor, failures)

    verification_commands = claim.get("verification_commands")
    if not isinstance(verification_commands, list) or not verification_commands:
        fail(failures, f"{claim_id}: verification_commands must be a non-empty list")
    else:
        for command in verification_commands:
            validate_command(claim_id, command, allowed_dev_commands, failures)

    return source_metric


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest.get("schema_version") != 1:
        fail(failures, "mvp-acceptance.json schema_version must be 1")

    source_doc_value = manifest.get("source_doc")
    section_name = manifest.get("acceptance_section")
    if not isinstance(source_doc_value, str):
        fail(failures, "source_doc must be a string")
        source_doc = REPO_ROOT / "__missing__"
    else:
        source_doc = REPO_ROOT / source_doc_value
    if not isinstance(section_name, str) or not section_name.strip():
        fail(failures, "acceptance_section must be a non-empty string")
        section_name = ""

    expected_metrics = source_acceptance_metrics(source_doc, section_name, failures)
    expected_metric_set = set(expected_metrics)

    allowed_dev_commands = dev_helper_commands()
    if not allowed_dev_commands:
        fail(failures, "could not parse commands from scripts/dev.sh")

    claims = manifest.get("claims")
    claim_metrics: list[str] = []
    if not isinstance(claims, list) or not claims:
        fail(failures, "claims must be a non-empty list")
    else:
        seen_ids: set[str] = set()
        for index, claim in enumerate(claims, 1):
            metric = validate_claim(claim, index, allowed_dev_commands, seen_ids, failures)
            if metric:
                claim_metrics.append(metric)

    claim_metric_set = set(claim_metrics)
    missing_metrics = sorted(expected_metric_set - claim_metric_set)
    extra_metrics = sorted(claim_metric_set - expected_metric_set)
    duplicate_metrics = sorted(metric for metric in claim_metric_set if claim_metrics.count(metric) > 1)

    if missing_metrics:
        fail(failures, "MVP acceptance metrics missing from manifest: " + "; ".join(missing_metrics))
    if extra_metrics:
        fail(failures, "manifest source_metric values not present in source doc: " + "; ".join(extra_metrics))
    if duplicate_metrics:
        fail(failures, "duplicate source_metric values in manifest: " + "; ".join(duplicate_metrics))

    if failures:
        print("MVP acceptance check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("MVP acceptance check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
