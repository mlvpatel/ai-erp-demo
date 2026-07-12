#!/usr/bin/env python3
"""Check local Markdown links without requiring network access.

The public repository docs should not link to files that are missing from the
source tree. External links are intentionally skipped so this check stays fast,
deterministic, and useful in offline CI.
"""

from __future__ import annotations

import re
import sys
import urllib.parse
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]

INLINE_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)")
SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
FENCE_PATTERN = re.compile(r"^\s*(```|~~~)")

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
}

SKIP_PREFIXES = {
    ("development", "frappe-bench"),
}


def is_skipped(path: Path) -> bool:
    rel_parts = path.relative_to(REPO_ROOT).parts
    if any(part in SKIP_DIRS for part in rel_parts):
        return True
    return any(rel_parts[: len(prefix)] == prefix for prefix in SKIP_PREFIXES)


def markdown_files() -> Iterable[Path]:
    for path in REPO_ROOT.rglob("*.md"):
        if not is_skipped(path):
            yield path


def extract_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if not target or target.startswith("#"):
        return None

    if target.startswith("<"):
        closing_angle = target.find(">")
        if closing_angle == -1:
            return target
        target = target[1:closing_angle].strip()
    else:
        target = target.split(None, 1)[0].strip()

    if not target or target.startswith("#"):
        return None
    if target.startswith("//") or SCHEME_PATTERN.match(target):
        return None

    target = target.split("#", 1)[0].split("?", 1)[0].strip()
    if not target:
        return None

    return urllib.parse.unquote(target)


def resolve_target(source: Path, target: str) -> Path:
    if target.startswith("/"):
        return REPO_ROOT / target.lstrip("/")
    return source.parent / target


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def iter_links(source: Path) -> Iterable[tuple[int, str, str]]:
    in_fenced_block = False
    lines = source.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, 1):
        if FENCE_PATTERN.match(line):
            in_fenced_block = not in_fenced_block
            continue
        if in_fenced_block:
            continue
        for match in INLINE_LINK_PATTERN.finditer(line):
            raw_target = match.group(1)
            target = extract_target(raw_target)
            if target is not None:
                yield line_number, raw_target, target


def main() -> int:
    failures: list[str] = []

    for source in markdown_files():
        for line_number, raw_target, target in iter_links(source):
            target_path = resolve_target(source, target)
            if not target_path.exists():
                source_rel = source.relative_to(REPO_ROOT)
                failures.append(
                    f"{source_rel}:{line_number}: missing local link target "
                    f"{raw_target!r} -> {display_path(target_path)}"
                )

    if failures:
        print("Markdown local link check failed:", file=sys.stderr)
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("Markdown local link check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
