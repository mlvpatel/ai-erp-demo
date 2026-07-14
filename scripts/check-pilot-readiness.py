#!/usr/bin/env python3
"""Validate truthful, synthetic-only service-pilot readiness evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "pilot-readiness.json"
EXPECTED_STATUS = "SYNTHETIC_REHEARSAL_READY_HUMAN_AND_DEPLOYMENT_GATES_PENDING"


def main() -> int:
    failures: list[str] = []
    try:
        value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Pilot readiness check failed: {exc}", file=sys.stderr)
        return 1

    if value.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if value.get("scope") != "service_operations":
        failures.append("scope must remain service_operations")
    if value.get("status") != EXPECTED_STATUS:
        failures.append(f"status must remain {EXPECTED_STATUS}")
    if value.get("data_mode") != "synthetic_only":
        failures.append("data_mode must remain synthetic_only")

    release_state = value.get("release_state")
    expected_release_state = {
        "automated_complete": False,
        "deployment_evidence_complete": False,
        "human_approval_pending": True,
        "pilot_approved": False,
    }
    if release_state != expected_release_state:
        failures.append(
            "release_state must distinguish incomplete automation/deployment evidence, pending human approval, and an unapproved pilot"
        )

    evidence = value.get("automated_evidence")
    expected_commands = {
        "scripts/dev.sh service-test",
        "scripts/dev.sh e2e-test",
        "scripts/dev.sh performance-smoke",
    }
    actual_commands: set[str] = set()
    if not isinstance(evidence, list) or not evidence:
        failures.append("automated_evidence must be a non-empty list")
    else:
        for entry in evidence:
            if not isinstance(entry, dict):
                failures.append("automated_evidence entries must be objects")
                continue
            command = entry.get("command")
            path = entry.get("path")
            if isinstance(command, str):
                actual_commands.add(command)
            if not isinstance(path, str) or not (ROOT / path).is_file():
                failures.append(f"automated evidence path is missing: {path!r}")
        if actual_commands != expected_commands:
            failures.append("automated evidence commands do not match service, E2E, and performance smoke")

    pending = value.get("pending_gates")
    owner_classes = {"business", "legal", "security", "operations", "accountable_owner"}
    required_gate_ids = {
        "design-partner-validation",
        "human-uat-signoff",
        "controller-processor-legal-basis",
        "dpa-dpia-transfer-review",
        "italian-counsel-or-dpo-review",
        "production-role-and-finance-separation",
        "rpo-rto-retention-approval",
        "restore-and-deletion-drill",
        "production-capacity-profile",
        "support-and-on-call-owner",
        "pilot-go-no-go",
    }
    actual_gate_ids: set[str] = set()
    if not isinstance(pending, list):
        failures.append("pending_gates must be a list")
    else:
        for gate in pending:
            if not isinstance(gate, dict):
                failures.append("pending gate entries must be objects")
                continue
            actual_gate_ids.add(str(gate.get("id")))
            if gate.get("status") != "pending":
                failures.append(f"gate must remain pending: {gate.get('id')}")
            if gate.get("owner_class") not in owner_classes:
                failures.append(f"invalid owner class for gate: {gate.get('id')}")
    if actual_gate_ids != required_gate_ids:
        failures.append("pending gate set is incomplete or contains an unknown gate")

    doc_fields = ("uat_doc", "evidence_template", "gdpr_gate", "aws_reference")
    combined_docs = ""
    for field in doc_fields:
        path = value.get(field)
        if not isinstance(path, str) or not (ROOT / path).is_file():
            failures.append(f"{field} must reference an existing file")
            continue
        combined_docs += "\n" + (ROOT / path).read_text(encoding="utf-8")

    for phrase in (
        "Human UAT: not performed",
        "Design-partner approval: pending",
        "Real data: prohibited",
        "neither GDPR compliance nor production approval",
    ):
        if phrase not in combined_docs:
            failures.append(f"pilot documents missing caveat: {phrase}")

    expected_claims = {"UAT passed", "design partner approved", "GDPR compliant", "production ready"}
    if set(value.get("forbidden_claims", [])) != expected_claims:
        failures.append("forbidden_claims must preserve all public-claim guardrails")

    if failures:
        print("Pilot readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("Pilot readiness check passed (synthetic rehearsal only; human/deployment gates pending).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
