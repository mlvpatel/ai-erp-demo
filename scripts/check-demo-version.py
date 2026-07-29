#!/usr/bin/env python3
"""Validate Demo Version packaging metadata and linked docs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "demo-version.json"
REQUIRED_KEYS = (
    "schema_version",
    "demo_version",
    "label",
    "claim_boundary",
    "product_shape",
    "data_mode",
    "ai_mode",
    "default_provider",
    "loop_doc",
    "stack_doc",
    "facilitator_runbook",
    "forbidden_claims",
)
REQUIRED_PATH_KEYS = (
    "scorecard_path",
    "pilot_readiness_path",
    "loop_doc",
    "stack_doc",
    "facilitator_runbook",
)


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def main() -> int:
    failures: list[str] = []
    try:
        manifest: dict[str, Any] = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"FAIL: missing {MANIFEST_PATH.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"FAIL: invalid JSON in demo-version.json: {exc}", file=sys.stderr)
        return 1

    if manifest.get("schema_version") != 1:
        fail(failures, "schema_version must be 1")

    for key in REQUIRED_KEYS:
        if key not in manifest:
            fail(failures, f"missing key: {key}")

    if manifest.get("label") != "Demo Version":
        fail(failures, "label must be 'Demo Version'")
    if manifest.get("data_mode") != "synthetic_only":
        fail(failures, "data_mode must be synthetic_only")
    if manifest.get("ai_mode") != "proposal_only":
        fail(failures, "ai_mode must be proposal_only")
    if manifest.get("default_provider") != "template":
        fail(failures, "default_provider must be template")
    if manifest.get("requires_live_openai") is not False:
        fail(failures, "requires_live_openai must be false")
    if manifest.get("requires_aws_apply") is not False:
        fail(failures, "requires_aws_apply must be false")

    demo_version = manifest.get("demo_version")
    if not isinstance(demo_version, str) or "-demo" not in demo_version:
        fail(failures, "demo_version must be a string containing '-demo'")

    claim = manifest.get("claim_boundary")
    if not isinstance(claim, str) or "not a production" not in claim.lower():
        fail(failures, "claim_boundary must state this is not a production release")

    for key in REQUIRED_PATH_KEYS:
        path_value = manifest.get(key)
        if not isinstance(path_value, str) or not path_value.strip():
            fail(failures, f"{key} must be a non-empty path string")
            continue
        if not (REPO_ROOT / path_value).exists():
            fail(failures, f"{key} path does not exist: {path_value}")

    forbidden = manifest.get("forbidden_claims")
    if not isinstance(forbidden, list) or len(forbidden) < 4:
        fail(failures, "forbidden_claims must list at least four claims")
    else:
        joined = " ".join(str(item).lower() for item in forbidden)
        for phrase in ("production ready", "gdpr compliant", "human uat"):
            if phrase not in joined:
                fail(failures, f"forbidden_claims must include {phrase!r}")

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    if "Demo Version" not in readme or "demo-version.json" not in readme:
        fail(failures, "README.md must mention Demo Version and demo-version.json")
    if "demo-version-loop.md" not in readme or "demo-version-stack.md" not in readme:
        fail(failures, "README.md must link demo-version-loop.md and demo-version-stack.md")

    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    if "demo-version-loop.md" not in agents:
        fail(failures, "AGENTS.md must reference demo-version-loop.md")

    if failures:
        print("Demo Version packaging check failed:", file=sys.stderr)
        for item in failures:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1

    print("Demo Version packaging check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
