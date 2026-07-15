#!/usr/bin/env python3
"""Scan publishable source files for secrets and sensitive-data indicators."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "publication-secret-scan.json"
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,}|localhost)\b")
ASSIGNMENT_PATTERN = re.compile(
    r"""
    ^\s*
    (?:
      ["']?(?P<key>[A-Za-z0-9_.-]+)["']?
    )
    \s*[:=]\s*
    (?P<value>[^#,\n]+?)
    \s*,?\s*$
    """,
    re.VERBOSE,
)


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


def read_text(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(failures, f"missing file: {rel(path)}")
    except UnicodeDecodeError as exc:
        fail(failures, f"expected UTF-8 text file: {rel(path)}: {exc}")
    return ""


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def contains_snippet(haystack: str, needle: str) -> bool:
    return normalize_space(needle) in normalize_space(haystack)


def as_string_list(value: Any, field: str, failures: list[str]) -> list[str]:
    if not isinstance(value, list):
        fail(failures, f"{field} must be a list")
        return []
    strings: list[str] = []
    for index, item in enumerate(value, 1):
        if not isinstance(item, str) or not item:
            fail(failures, f"{field}[{index}] must be a non-empty string")
            continue
        strings.append(item)
    return strings


def compile_patterns(manifest: dict[str, Any], failures: list[str]) -> list[tuple[str, re.Pattern[str]]]:
    compiled: list[tuple[str, re.Pattern[str]]] = []
    patterns = manifest.get("secret_patterns")
    if not isinstance(patterns, list) or not patterns:
        fail(failures, "secret_patterns must be a non-empty list")
        return compiled

    seen_ids: set[str] = set()
    for index, entry in enumerate(patterns, 1):
        if not isinstance(entry, dict):
            fail(failures, f"secret_patterns[{index}] must be an object")
            continue
        pattern_id = entry.get("id")
        regex = entry.get("regex")
        if not isinstance(pattern_id, str) or not pattern_id:
            fail(failures, f"secret_patterns[{index}].id must be a non-empty string")
            pattern_id = f"secret_patterns[{index}]"
        elif pattern_id in seen_ids:
            fail(failures, f"duplicate secret pattern id: {pattern_id}")
        seen_ids.add(pattern_id)
        if not isinstance(regex, str) or not regex:
            fail(failures, f"{pattern_id}: regex must be a non-empty string")
            continue
        try:
            compiled.append((pattern_id, re.compile(regex)))
        except re.error as exc:
            fail(failures, f"{pattern_id}: invalid regex: {exc}")
    return compiled


def validate_shape(manifest: dict[str, Any], failures: list[str]) -> None:
    if manifest.get("schema_version") != 1:
        fail(failures, "publication-secret-scan.json schema_version must be 1")
    if manifest.get("scanner_script") != "scripts/check-publication-secrets.py":
        fail(failures, "scanner_script must be scripts/check-publication-secrets.py")

    for field in (
        "scan_targets",
        "text_file_suffixes",
        "text_file_names",
        "excluded_path_prefixes",
        "excluded_path_suffixes",
        "forbidden_tracked_path_prefixes",
        "forbidden_tracked_path_suffixes",
        "required_local_only_exclusions",
        "sensitive_assignment_keys",
        "allowed_assignment_value_patterns",
        "allowed_email_domain_suffixes",
    ):
        as_string_list(manifest.get(field), field, failures)

    required_exclusions = {
        ".env",
        ".env.*",
        "*.pem",
        "*.key",
        "*.sql",
        "*.sql.gz",
        "*.dump",
        "*.backup",
        "*-files.tar",
        "*-private-files.tar",
        "development/.env",
        "development/frappe-bench/",
        "config/owner-decisions.local.json",
        "sites/",
        "logs/",
        "private/",
        "public/assets/",
    }
    actual_exclusions = set(as_string_list(manifest.get("required_local_only_exclusions"), "required_local_only_exclusions", failures))
    missing = sorted(required_exclusions - actual_exclusions)
    if missing:
        fail(failures, "required_local_only_exclusions missing: " + ", ".join(missing))

    policy_documents = manifest.get("policy_documents")
    if not isinstance(policy_documents, list) or not policy_documents:
        fail(failures, "policy_documents must be a non-empty list")
    else:
        for index, entry in enumerate(policy_documents, 1):
            if not isinstance(entry, dict):
                fail(failures, f"policy_documents[{index}] must be an object")
                continue
            path = entry.get("path")
            if not isinstance(path, str) or not path:
                fail(failures, f"policy_documents[{index}].path must be a non-empty string")
            as_string_list(entry.get("required_phrases"), f"policy_documents[{index}].required_phrases", failures)

    compile_patterns(manifest, failures)
    for index, pattern in enumerate(as_string_list(manifest.get("allowed_assignment_value_patterns"), "allowed_assignment_value_patterns", failures), 1):
        try:
            re.compile(pattern, flags=re.IGNORECASE)
        except re.error as exc:
            fail(failures, f"allowed_assignment_value_patterns[{index}] invalid regex: {exc}")


def is_under_prefix(path_text: str, prefixes: Iterable[str]) -> bool:
    for prefix in prefixes:
        normalized = prefix[2:] if prefix.startswith("./") else prefix
        if normalized.endswith("/"):
            if path_text.startswith(normalized):
                return True
        elif path_text == normalized or path_text.startswith(normalized + "/"):
            return True
    return False


def should_exclude(path: Path, manifest: dict[str, Any]) -> bool:
    path_text = rel(path)
    prefixes = manifest.get("excluded_path_prefixes", [])
    suffixes = manifest.get("excluded_path_suffixes", [])
    if isinstance(prefixes, list) and is_under_prefix(
        path_text,
        (item for item in prefixes if isinstance(item, str)),
    ):
        return True
    if isinstance(suffixes, list) and any(path_text.endswith(suffix) for suffix in suffixes if isinstance(suffix, str)):
        return True
    return "__pycache__" in path.parts


def is_text_file(path: Path, manifest: dict[str, Any]) -> bool:
    suffixes = set(as_string for as_string in manifest.get("text_file_suffixes", []) if isinstance(as_string, str))
    names = set(as_string for as_string in manifest.get("text_file_names", []) if isinstance(as_string, str))
    return path.name in names or path.suffix in suffixes


def iter_scan_files(manifest: dict[str, Any], failures: list[str]) -> list[Path]:
    files: list[Path] = []
    targets = as_string_list(manifest.get("scan_targets"), "scan_targets", failures)
    for target in targets:
        path = REPO_ROOT / target
        if not path.exists():
            fail(failures, f"scan target is missing: {target}")
            continue
        if path.is_file():
            if not should_exclude(path, manifest) and is_text_file(path, manifest):
                files.append(path)
            continue
        if not path.is_dir():
            fail(failures, f"scan target must be a file or directory: {target}")
            continue
        for child in path.rglob("*"):
            if child.is_file() and not should_exclude(child, manifest) and is_text_file(child, manifest):
                files.append(child)
    return sorted(set(files))


def git_tracked_files() -> list[str] | None:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if tracked.returncode != 0:
        return []
    return [line for line in tracked.stdout.splitlines() if line]


def validate_forbidden_tracked_paths(manifest: dict[str, Any], failures: list[str]) -> None:
    tracked = git_tracked_files()
    if tracked is None:
        return

    prefixes = as_string_list(
        manifest.get("forbidden_tracked_path_prefixes"),
        "forbidden_tracked_path_prefixes",
        failures,
    )
    suffixes = as_string_list(
        manifest.get("forbidden_tracked_path_suffixes"),
        "forbidden_tracked_path_suffixes",
        failures,
    )
    findings: list[str] = []
    for path_text in tracked:
        if is_under_prefix(path_text, prefixes) or any(path_text.endswith(suffix) for suffix in suffixes):
            if path_text != ".env.example":
                findings.append(path_text)

    if findings:
        fail(failures, "forbidden local/secret-like paths are tracked:\n" + "\n".join(sorted(findings)))


def normalize_assignment_value(value: str) -> str:
    normalized = value.strip().rstrip(",").strip()
    if (normalized.startswith('"') and normalized.endswith('"')) or (
        normalized.startswith("'") and normalized.endswith("'")
    ):
        normalized = normalized[1:-1]
    return normalized.strip()


def sensitive_key(key: str, manifest: dict[str, Any]) -> bool:
    normalized_key = key.lower().replace("-", "_").replace(".", "_")
    allowed_non_secret = manifest.get("allowed_non_secret_assignment_keys", [])
    if isinstance(allowed_non_secret, list) and normalized_key in {
        item for item in allowed_non_secret if isinstance(item, str)
    }:
        return False
    if key != key.lower() and key != key.upper():
        return False
    configured = manifest.get("sensitive_assignment_keys", [])
    if not isinstance(configured, list):
        return False
    configured_strings = [item for item in configured if isinstance(item, str)]
    if normalized_key in configured_strings:
        return True
    high_signal_terms = {
        "access_key",
        "admin_password",
        "api_key",
        "client_secret",
        "db_root_password",
        "password",
        "private_key",
        "secret",
        "shared_secret",
    }
    if any(term in normalized_key for term in high_signal_terms):
        return True
    token_terms = {"access_token", "auth_token", "bearer_token", "refresh_token"}
    if any(term in normalized_key for term in token_terms):
        return True
    return key == key.upper() and normalized_key.endswith("_token")


def allowed_sensitive_value(value: str, manifest: dict[str, Any]) -> bool:
    if value.startswith("[") or value.startswith("{"):
        return True
    patterns = manifest.get("allowed_assignment_value_patterns", [])
    if not isinstance(patterns, list):
        return False
    return any(
        isinstance(pattern, str) and re.fullmatch(pattern, value, flags=re.IGNORECASE)
        for pattern in patterns
    )


def scan_sensitive_assignments(path: Path, text: str, manifest: dict[str, Any], failures: list[str]) -> None:
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
            continue
        # A quoted scalar in a list can contain a colon (for example an IAM
        # action) but is not a key/value assignment.
        if re.fullmatch(r'''["'][^"']+["'],?''', stripped):
            continue
        match = ASSIGNMENT_PATTERN.match(line)
        if not match:
            continue
        key = match.group("key")
        value = normalize_assignment_value(match.group("value"))
        if not key or not sensitive_key(key, manifest):
            continue
        if allowed_sensitive_value(value, manifest):
            continue
        fail(
            failures,
            f"{rel(path)}:{line_no}: sensitive key {key!r} has a non-placeholder value",
        )


def scan_secret_patterns(
    path: Path,
    text: str,
    patterns: list[tuple[str, re.Pattern[str]]],
    failures: list[str],
) -> None:
    for pattern_id, pattern in patterns:
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            fail(failures, f"{rel(path)}:{line_no}: possible secret pattern matched: {pattern_id}")


def allowed_email_domain(domain: str, manifest: dict[str, Any]) -> bool:
    allowed = manifest.get("allowed_email_domain_suffixes", [])
    if not isinstance(allowed, list):
        return False
    normalized = domain.lower()
    for suffix in allowed:
        if not isinstance(suffix, str):
            continue
        suffix = suffix.lower().lstrip(".")
        if normalized == suffix or normalized.endswith("." + suffix):
            return True
    return False


def scan_email_domains(path: Path, text: str, manifest: dict[str, Any], failures: list[str]) -> None:
    for match in EMAIL_PATTERN.finditer(text):
        domain = match.group(1)
        if allowed_email_domain(domain, manifest):
            continue
        line_no = text.count("\n", 0, match.start()) + 1
        fail(
            failures,
            f"{rel(path)}:{line_no}: email domain {domain!r} is not an allowed public or synthetic domain",
        )


def validate_policy_documents(manifest: dict[str, Any], failures: list[str]) -> None:
    policy_documents = manifest.get("policy_documents", [])
    if not isinstance(policy_documents, list):
        return
    for entry in policy_documents:
        if not isinstance(entry, dict):
            continue
        path_value = entry.get("path")
        if not isinstance(path_value, str):
            continue
        text = read_text(REPO_ROOT / path_value, failures)
        if not text:
            continue
        phrases = entry.get("required_phrases", [])
        if not isinstance(phrases, list):
            continue
        for phrase in phrases:
            if isinstance(phrase, str) and not contains_snippet(text, phrase):
                fail(failures, f"{path_value}: missing publication safety phrase: {phrase}")


def scan_files(manifest: dict[str, Any], failures: list[str]) -> None:
    patterns = compile_patterns(manifest, failures)
    files = iter_scan_files(manifest, failures)
    for path in files:
        text = read_text(path, failures)
        if not text:
            continue
        scan_secret_patterns(path, text, patterns, failures)
        scan_sensitive_assignments(path, text, manifest, failures)
        scan_email_domains(path, text, manifest, failures)


def main() -> int:
    failures: list[str] = []
    manifest = load_json(MANIFEST_PATH, failures)

    if manifest:
        validate_shape(manifest, failures)
        validate_forbidden_tracked_paths(manifest, failures)
        validate_policy_documents(manifest, failures)
        scan_files(manifest, failures)

    if failures:
        print("Publication secret and sensitive-data scan failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Publication secret and sensitive-data scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
