#!/usr/bin/env python3
"""Validate the owner-decision template and optional local decision file."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = REPO_ROOT / "config" / "owner-decisions.example.json"
LOCAL_PATH = REPO_ROOT / "config" / "owner-decisions.local.json"
GITIGNORE_PATH = REPO_ROOT / ".gitignore"

ALLOWED_LICENSE_POLICIES = {
    "MIT",
    "AGPL-3.0-only",
    "GPL-3.0-only",
    "custom-split-policy",
}
ALLOWED_RELEASE_TYPES = {
    "source-only-developer-demo",
    "tagged-runnable-preview",
}
ALLOWED_CONTRIBUTION_POLICIES = {
    "DCO",
    "CLA",
    "none-before-publication",
}
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
REPO_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
PLACEHOLDER_TERMS = {
    "example",
    "replace",
    "todo",
    "tbd",
    "owner",
    "your-",
    "placeholder",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def load_json(path: Path, failures: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(failures, f"missing JSON file: {rel(path)}")
        return None
    except json.JSONDecodeError as exc:
        fail(failures, f"invalid JSON in {rel(path)}: {exc}")
        return None
    if not isinstance(value, dict):
        fail(failures, f"{rel(path)} must contain a JSON object")
        return None
    return value


def is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in PLACEHOLDER_TERMS)


def require_string(
    data: dict[str, Any],
    field: str,
    failures: list[str],
    context: str,
    *,
    allow_example: bool,
) -> str | None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        fail(failures, f"{context}: {field} must be a non-empty string")
        return None
    if not allow_example and is_placeholder(value):
        fail(failures, f"{context}: {field} still looks like an example or placeholder value")
    return value


def validate_decision_file(data: dict[str, Any], failures: list[str], context: str, *, local: bool) -> None:
    if data.get("schema_version") != 1:
        fail(failures, f"{context}: schema_version must be 1")

    expected_status = "selected" if local else "example-only"
    if data.get("decision_status") != expected_status:
        fail(failures, f"{context}: decision_status must be {expected_status!r}")

    license_policy = require_string(
        data, "license_policy", failures, context, allow_example=not local
    )
    if license_policy and license_policy not in ALLOWED_LICENSE_POLICIES:
        fail(
            failures,
            f"{context}: license_policy must be one of {', '.join(sorted(ALLOWED_LICENSE_POLICIES))}",
        )

    copyright_year = require_string(
        data, "copyright_year", failures, context, allow_example=not local
    )
    if copyright_year and not re.fullmatch(r"20[0-9]{2}", copyright_year):
        fail(failures, f"{context}: copyright_year must be a four-digit year")

    require_string(data, "copyright_holder", failures, context, allow_example=not local)

    email = require_string(data, "public_contact_email", failures, context, allow_example=not local)
    if email and not EMAIL_PATTERN.match(email):
        fail(failures, f"{context}: public_contact_email is not a valid email shape")
    if local and email and email.endswith(("@example.org", "@example.com", "@example.test")):
        fail(failures, f"{context}: public_contact_email must not use an example domain")

    repository_owner = require_string(
        data, "repository_owner", failures, context, allow_example=not local
    )
    if repository_owner and "/" in repository_owner:
        fail(failures, f"{context}: repository_owner must not include a slash")

    repository_name = require_string(
        data, "repository_name", failures, context, allow_example=not local
    )
    if repository_name and not REPO_NAME_PATTERN.match(repository_name):
        fail(failures, f"{context}: repository_name contains invalid characters")

    default_branch = require_string(
        data, "default_branch", failures, context, allow_example=not local
    )
    if default_branch != "main":
        fail(failures, f"{context}: default_branch must stay aligned with repository metadata: main")

    release_type = require_string(
        data, "public_release_type", failures, context, allow_example=not local
    )
    if release_type and release_type not in ALLOWED_RELEASE_TYPES:
        fail(
            failures,
            f"{context}: public_release_type must be one of {', '.join(sorted(ALLOWED_RELEASE_TYPES))}",
        )

    contribution_policy = require_string(
        data, "contribution_policy", failures, context, allow_example=not local
    )
    if contribution_policy and contribution_policy not in ALLOWED_CONTRIBUTION_POLICIES:
        fail(
            failures,
            f"{context}: contribution_policy must be one of {', '.join(sorted(ALLOWED_CONTRIBUTION_POLICIES))}",
        )

    maintainers = data.get("initial_maintainers")
    if not isinstance(maintainers, list) or not maintainers:
        fail(failures, f"{context}: initial_maintainers must be a non-empty list")
    else:
        for index, maintainer in enumerate(maintainers, 1):
            if not isinstance(maintainer, str) or not maintainer.strip():
                fail(failures, f"{context}: initial_maintainers[{index}] must be a non-empty string")
            elif local and is_placeholder(maintainer):
                fail(failures, f"{context}: initial_maintainers[{index}] still looks like an example value")

    notes = data.get("notes", [])
    if not isinstance(notes, list):
        fail(failures, f"{context}: notes must be a list when present")
    elif any(not isinstance(note, str) for note in notes):
        fail(failures, f"{context}: every note must be a string")


def validate_gitignore(failures: list[str]) -> None:
    try:
        patterns = set(GITIGNORE_PATH.read_text(encoding="utf-8").splitlines())
    except FileNotFoundError:
        fail(failures, "missing .gitignore")
        return
    if "config/owner-decisions.local.json" not in patterns:
        fail(failures, ".gitignore must exclude config/owner-decisions.local.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="require config/owner-decisions.local.json and validate it as real selected owner decisions",
    )
    args = parser.parse_args()

    failures: list[str] = []
    validate_gitignore(failures)

    example = load_json(EXAMPLE_PATH, failures)
    if example is not None:
        validate_decision_file(example, failures, rel(EXAMPLE_PATH), local=False)

    if LOCAL_PATH.exists():
        local = load_json(LOCAL_PATH, failures)
        if local is not None:
            validate_decision_file(local, failures, rel(LOCAL_PATH), local=True)
    elif args.strict:
        fail(
            failures,
            "config/owner-decisions.local.json is required in --strict mode; copy the example and replace values",
        )

    if failures:
        print("Owner decision check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    if LOCAL_PATH.exists():
        print("Owner decision check passed with local decisions present.")
    else:
        print("Owner decision template check passed; local owner decisions are still pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
