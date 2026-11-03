#!/usr/bin/env python3
"""Validate license/contact metadata targets without choosing the license."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from typing import Any

from _gate import REPO_ROOT, load_json_object, read_text


MANIFEST_PATH = REPO_ROOT / "config" / "license-metadata.json"
OWNER_DECISIONS_PATH = REPO_ROOT / "config" / "owner-decisions.local.json"
LICENSE_RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "license-decision.md"
DEFAULT_PLACEHOLDER_PATTERN = re.compile(r"(\[year\]|\[fullname\]|opensource@ai-erp\.example)")
HOOK_EMAIL_PATTERN = re.compile(r'^app_email\s*=\s*"([^"]+)"', re.MULTILINE)
HOOK_LICENSE_PATTERN = re.compile(r'^app_license\s*=\s*"([^"]+)"', re.MULTILINE)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)


def manifest_paths(manifest: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for path in manifest.get("root_targets", []):
        if isinstance(path, str):
            paths.add(path)
    for app in manifest.get("frappe_apps", []):
        if isinstance(app, dict):
            for field in ("hook_path", "pyproject_path", "license_path", "readme_path"):
                value = app.get(field)
                if isinstance(value, str):
                    paths.add(value)
    for service in manifest.get("python_services", []):
        if isinstance(service, dict):
            value = service.get("pyproject_path")
            if isinstance(value, str):
                paths.add(value)
    return paths


def current_placeholder_locations(paths: set[str]) -> list[str]:
    findings: list[str] = []
    for value in sorted(paths):
        path = REPO_ROOT / value
        if not path.is_file():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if DEFAULT_PLACEHOLDER_PATTERN.search(line):
                findings.append(f"{value}:{line_no}:{line}")
    return findings


def validate_manifest_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    status = manifest.get("status")
    if status != "selected":
        failures.append("license-metadata.json status must be selected")

    placeholders = manifest.get("placeholder_patterns")
    if not isinstance(placeholders, list) or not placeholders:
        failures.append("placeholder_patterns must be a non-empty list")
    else:
        for required in ("[year]", "[fullname]", "opensource@ai-erp.example"):
            if required not in placeholders:
                failures.append(f"placeholder_patterns must include {required!r}")

    policies = manifest.get("policies")
    if not isinstance(policies, dict) or not policies:
        failures.append("policies must be a non-empty object")
    else:
        for policy, data in policies.items():
            if not isinstance(data, dict):
                failures.append(f"{policy}: policy metadata must be an object")
                continue
            if not isinstance(data.get("display"), str) or not data["display"].strip():
                failures.append(f"{policy}: display must be non-empty")
            if not isinstance(data.get("frappe_app_license"), str) or not data["frappe_app_license"].strip():
                failures.append(f"{policy}: frappe_app_license must be non-empty")
            hint = data.get("root_license_hint")
            if hint is not None and not isinstance(hint, str):
                failures.append(f"{policy}: root_license_hint must be string or null")

    if status == "selected":
        selected_policy = manifest.get("selected_policy")
        if not isinstance(selected_policy, str) or not isinstance(policies, dict) or selected_policy not in policies:
            failures.append("selected_policy must name a policy from license-metadata.json")
        for field in ("copyright_year", "copyright_holder", "public_contact_email"):
            value = manifest.get(field)
            if not isinstance(value, str) or not value.strip():
                failures.append(f"selected license metadata requires non-empty {field}")

    if not isinstance(manifest.get("root_targets"), list) or "LICENSE" not in manifest.get("root_targets", []):
        failures.append("root_targets must include LICENSE")

    apps = manifest.get("frappe_apps")
    if not isinstance(apps, list) or not apps:
        failures.append("frappe_apps must be a non-empty list")
    else:
        for index, app in enumerate(apps, 1):
            if not isinstance(app, dict):
                failures.append(f"frappe_apps[{index}] must be an object")
                continue
            for field in ("name", "hook_path", "pyproject_path", "license_path", "readme_path"):
                if not isinstance(app.get(field), str) or not app[field].strip():
                    failures.append(f"frappe_apps[{index}].{field} must be a non-empty string")

    services = manifest.get("python_services")
    if not isinstance(services, list):
        failures.append("python_services must be a list")
    else:
        for index, service in enumerate(services, 1):
            if not isinstance(service, dict):
                failures.append(f"python_services[{index}] must be an object")
                continue
            for field in ("name", "pyproject_path"):
                if not isinstance(service.get(field), str) or not service[field].strip():
                    failures.append(f"python_services[{index}].{field} must be a non-empty string")


def validate_target_files(manifest: dict[str, Any], failures: list[str]) -> None:
    paths = manifest_paths(manifest)
    runbook = read_text(LICENSE_RUNBOOK, failures)
    for value in sorted(paths):
        path = REPO_ROOT / value
        if value == "LICENSE":
            continue
        if not path.is_file():
            failures.append(f"license metadata target missing: {value}")
        if value not in runbook:
            failures.append(f"license decision runbook must mention metadata target: {value}")


def load_owner_decisions(failures: list[str]) -> dict[str, Any] | None:
    result = run(["python3", "scripts/check-owner-decisions.py", "--strict"])
    if result.returncode != 0:
        failures.append("owner decisions are required for strict license metadata check:\n" + result.stderr.strip())
        return None
    return load_json_object(OWNER_DECISIONS_PATH, failures)


def value_from_regex(pattern: re.Pattern[str], source: str) -> str | None:
    match = pattern.search(source)
    if match:
        return match.group(1)
    return None


def validate_reconciled_state(
    manifest: dict[str, Any], owner: dict[str, Any], failures: list[str]
) -> None:
    policy_name = owner.get("license_policy")
    policies = manifest.get("policies", {})
    if not isinstance(policy_name, str) or policy_name not in policies:
        failures.append("owner license_policy must exist in config/license-metadata.json policies")
        return
    policy = policies[policy_name]

    root_license = REPO_ROOT / "LICENSE"
    if not root_license.is_file():
        failures.append("strict license metadata requires root LICENSE")
    else:
        hint = policy.get("root_license_hint")
        if isinstance(hint, str) and hint not in root_license.read_text(encoding="utf-8"):
            failures.append(f"root LICENSE does not contain expected policy hint: {hint}")

    placeholders = current_placeholder_locations(manifest_paths(manifest))
    if placeholders:
        failures.append("license/contact placeholders remain:\n" + "\n".join(placeholders))

    public_email = owner.get("public_contact_email")
    copyright_line = f"Copyright (c) {owner.get('copyright_year')} {owner.get('copyright_holder')}"
    expected_hook_license = policy.get("frappe_app_license")
    display = policy.get("display")

    for app in manifest.get("frappe_apps", []):
        if not isinstance(app, dict):
            continue
        hook_path = REPO_ROOT / app["hook_path"]
        hook_text = read_text(hook_path, failures)
        hook_email = value_from_regex(HOOK_EMAIL_PATTERN, hook_text)
        hook_license = value_from_regex(HOOK_LICENSE_PATTERN, hook_text)
        if hook_email != public_email:
            failures.append(f"{app['hook_path']}: app_email must match owner public_contact_email")
        if expected_hook_license and hook_license != expected_hook_license:
            failures.append(f"{app['hook_path']}: app_license must be {expected_hook_license!r}")

        pyproject_text = read_text(REPO_ROOT / app["pyproject_path"], failures)
        if isinstance(public_email, str) and public_email not in pyproject_text:
            failures.append(f"{app['pyproject_path']}: public contact email missing")
        if isinstance(display, str) and display not in pyproject_text:
            failures.append(f"{app['pyproject_path']}: selected license display missing")

        license_text = read_text(REPO_ROOT / app["license_path"], failures)
        if copyright_line not in license_text:
            failures.append(f"{app['license_path']}: copyright line does not match owner decisions")

        readme_text = read_text(REPO_ROOT / app["readme_path"], failures)
        if isinstance(display, str) and display not in readme_text:
            failures.append(f"{app['readme_path']}: license section must mention {display}")

    for service in manifest.get("python_services", []):
        if not isinstance(service, dict):
            continue
        pyproject_text = read_text(REPO_ROOT / service["pyproject_path"], failures)
        if isinstance(public_email, str) and public_email not in pyproject_text:
            failures.append(f"{service['pyproject_path']}: public contact email missing")
        if isinstance(display, str) and display not in pyproject_text:
            failures.append(f"{service['pyproject_path']}: selected license display missing")


def public_selected_metadata(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "license_policy": manifest.get("selected_policy"),
        "copyright_year": manifest.get("copyright_year"),
        "copyright_holder": manifest.get("copyright_holder"),
        "public_contact_email": manifest.get("public_contact_email"),
    }


def validate_selected_state(manifest: dict[str, Any], failures: list[str]) -> None:
    validate_reconciled_state(manifest, public_selected_metadata(manifest), failures)


def validate_strict_state(manifest: dict[str, Any], failures: list[str]) -> None:
    owner = load_owner_decisions(failures)
    if owner is None:
        return

    if manifest.get("status") == "selected":
        for public_field, owner_field in (
            ("selected_policy", "license_policy"),
            ("copyright_year", "copyright_year"),
            ("copyright_holder", "copyright_holder"),
            ("public_contact_email", "public_contact_email"),
        ):
            if manifest.get(public_field) != owner.get(owner_field):
                failures.append(
                    f"public {public_field} must match owner decision {owner_field}",
                )

    validate_reconciled_state(manifest, owner, failures)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="require owner decisions and reconciled public license/contact metadata",
    )
    args = parser.parse_args()

    failures: list[str] = []
    manifest = load_json_object(MANIFEST_PATH, failures)
    if manifest is not None:
        validate_manifest_shape(manifest, failures)
        validate_target_files(manifest, failures)
        if args.strict:
            validate_strict_state(manifest, failures)
        else:
            validate_selected_state(manifest, failures)

    if failures:
        label = "Strict license metadata check failed" if args.strict else "License metadata check failed"
        print(label + ":", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    if args.strict:
        print("Strict license metadata check passed.")
    else:
        print("License metadata check passed; AGPL-3.0-only is selected and reconciled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
