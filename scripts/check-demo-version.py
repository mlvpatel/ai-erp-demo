#!/usr/bin/env python3
"""Validate Demo Version packaging metadata and linked docs."""

from __future__ import annotations

import json
import sys
from typing import Any

from _gate import REPO_ROOT, report


MANIFEST_PATH = REPO_ROOT / "config" / "demo-version.json"
REQUIRED_KEYS = (
    "demo_version",
    "claim_boundary",
    "product_shape",
    "loop_doc",
    "stack_doc",
    "facilitator_runbook",
    "forbidden_claims",
)
REQUIRED_PATH_KEYS = (
    "loop_doc",
    "stack_doc",
    "facilitator_runbook",
)


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


    for key in REQUIRED_KEYS:
        if key not in manifest:
            failures.append(f"missing key: {key}")

    demo_version = manifest.get("demo_version")
    if not isinstance(demo_version, str) or "-demo" not in demo_version:
        failures.append("demo_version must be a string containing '-demo'")

    claim = manifest.get("claim_boundary")
    if not isinstance(claim, str) or "not a production" not in claim.lower():
        failures.append("claim_boundary must state this is not a production release")

    for key in REQUIRED_PATH_KEYS:
        path_value = manifest.get(key)
        if not isinstance(path_value, str) or not path_value.strip():
            failures.append(f"{key} must be a non-empty path string")
            continue
        if not (REPO_ROOT / path_value).exists():
            failures.append(f"{key} path does not exist: {path_value}")

    forbidden = manifest.get("forbidden_claims")
    if not isinstance(forbidden, list) or len(forbidden) < 4:
        failures.append("forbidden_claims must list at least four claims")
    else:
        joined = " ".join(str(item).lower() for item in forbidden)
        for phrase in ("production ready", "gdpr compliant", "human uat"):
            if phrase not in joined:
                failures.append(f"forbidden_claims must include {phrase!r}")

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    if "Demo Version" not in readme or "demo-version.json" not in readme:
        failures.append("README.md must mention Demo Version and demo-version.json")
    if "demo-version-loop.md" not in readme or "demo-version-stack.md" not in readme:
        failures.append("README.md must link demo-version-loop.md and demo-version-stack.md")

    return report("Demo Version packaging check", failures)


if __name__ == "__main__":
    raise SystemExit(main())
