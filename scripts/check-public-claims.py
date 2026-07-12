#!/usr/bin/env python3
"""Check that public-facing claims match the current repo state.

This guardrail intentionally avoids judging marketing copy. Instead, it verifies
specific release blockers and safety disclaimers that must remain true until
the owner resolves licensing and the project proves more than the first
service-operations vertical.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

README = REPO_ROOT / "README.md"
PUBLIC_POSITIONING = REPO_ROOT / "docs" / "product" / "public-positioning.md"
TRACEABILITY = REPO_ROOT / "docs" / "product" / "requirements-traceability.md"
GITHUB_PUBLICATION = REPO_ROOT / "docs" / "runbooks" / "github-publication.md"
INDUSTRY_PACKS = REPO_ROOT / "config" / "industry-packs.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalized(text: str) -> str:
    return " ".join(text.split())


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def require_contains(failures: list[str], path: Path, needle: str) -> None:
    text = normalized(read(path))
    if normalized(needle) not in text:
        fail(failures, f"{path.relative_to(REPO_ROOT)} must contain: {needle!r}")


def require_traceability_status(
    failures: list[str], requirement: str, expected_status: str
) -> None:
    text = read(TRACEABILITY)
    pattern = re.compile(
        rf"^\| {re.escape(requirement)} \| {re.escape(expected_status)} \|",
        re.MULTILINE,
    )
    if not pattern.search(text):
        fail(
            failures,
            "requirements traceability must keep "
            f"{requirement!r} at status {expected_status!r}",
        )


def validate_license_blockers(failures: list[str]) -> None:
    if not (REPO_ROOT / "LICENSE").exists():
        require_contains(failures, README, "The root license is intentionally pending owner selection")
        require_contains(failures, README, "Use `scripts/check-open-source-ready.sh --release` only after the root license")
        require_contains(failures, GITHUB_PUBLICATION, "The root `LICENSE` exists and matches ADR-0005's resolved decision")
        require_traceability_status(failures, "Publish publicly on GitHub.", "Blocked")


def validate_public_positioning(failures: list[str]) -> None:
    required_claim_boundaries = [
        "Do not claim this is production-ready.",
        "Do not claim autonomous ERP posting or autonomous customer messaging.",
        "Do not claim broad all-industry coverage",
        "repository-owned code is licensed under `AGPL-3.0-only`",
        "starting with a service-operations industry workflow",
    ]
    for boundary in required_claim_boundaries:
        require_contains(failures, PUBLIC_POSITIONING, boundary)

    require_contains(
        failures,
        PUBLIC_POSITIONING,
        "AI drafts, explains, classifies, retrieves, and proposes; it does not directly post",
    )


def validate_industry_scope(failures: list[str]) -> None:
    try:
        manifest = json.loads(INDUSTRY_PACKS.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(failures, "industry-pack manifest is missing")
        return
    except json.JSONDecodeError as exc:
        fail(failures, f"industry-pack manifest is invalid JSON: {exc}")
        return

    packs = manifest.get("packs", [])
    implemented = [pack for pack in packs if isinstance(pack, dict) and pack.get("status") == "implemented"]
    if len(implemented) != 1 or implemented[0].get("id") != "field_service":
        fail(
            failures,
            "public claims currently assume exactly one implemented pack: field_service",
        )

    require_traceability_status(
        failures,
        "Build an AI ERP system for broad industry expansion.",
        "Prepared",
    )
    require_contains(
        failures,
        TRACEABILITY,
        "Broad industry coverage is roadmap-driven, not yet claimed as implemented.",
    )


def validate_release_runbook(failures: list[str]) -> None:
    required_gate_phrases = [
        "Generated app and Python package license/contact metadata no longer contain",
        "Local generated artifacts have been cleaned or excluded from the publication",
        "The public roadmap and positioning describe implemented service-operations",
        "The AI control plane remains draft-only and cannot directly post financial",
    ]
    for phrase in required_gate_phrases:
        require_contains(failures, GITHUB_PUBLICATION, phrase)


def main() -> int:
    failures: list[str] = []

    for path in (README, PUBLIC_POSITIONING, TRACEABILITY, GITHUB_PUBLICATION):
        if not path.exists():
            fail(failures, f"required public-claim source is missing: {path.relative_to(REPO_ROOT)}")

    if not failures:
        validate_license_blockers(failures)
        validate_public_positioning(failures)
        validate_industry_scope(failures)
        validate_release_runbook(failures)

    if failures:
        print("Public claims check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Public claims check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
