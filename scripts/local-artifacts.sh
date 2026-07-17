#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: scripts/local-artifacts.sh [--check|--count|--clean]

Lists ignored local artifacts created by Python, tests, and packaging tools.

Options:
  --check   Exit 1 when artifacts are present.
  --count   Print only the artifact count.
  --clean   Delete listed artifacts. Use only after reviewing the list.
USAGE
}

list_artifacts() {
  cd "$repo_root"
  find . \
    \( -path './.git' -o -path './development/frappe-bench' \) -prune -o \
    \( -type d \( \
      -name '__pycache__' -o \
      -name '.pytest_cache' -o \
      -name '.mypy_cache' -o \
      -name '.ruff_cache' -o \
      -name 'node_modules' -o \
      -name 'playwright-report' -o \
      -name 'test-results' -o \
      -name '*.egg-info' -o \
      -name 'build' -o \
      -name 'dist' \
    \) -print -prune \) -o \
    \( -type f \( \
      -name '*.pyc' -o \
      -name '*.pyo' -o \
      -name '.coverage' \
    \) -print \) |
    sort
}

artifact_count() {
  list_artifacts | awk 'END { print NR + 0 }'
}

command="${1:-list}"
case "$command" in
  list)
    list_artifacts
    ;;
  --check)
    count="$(artifact_count)"
    if [ "$count" -ne 0 ]; then
      list_artifacts >&2
      echo "Found $count local generated artifact(s). Run scripts/local-artifacts.sh --clean before publishing an archive." >&2
      exit 1
    fi
    echo "No local generated artifacts found."
    ;;
  --count)
    artifact_count
    ;;
  --clean)
    artifact_file="$(mktemp)"
    list_artifacts > "$artifact_file"
    if [ ! -s "$artifact_file" ]; then
      rm -f "$artifact_file"
      echo "No local generated artifacts found."
      exit 0
    fi
    cat "$artifact_file"
    while IFS= read -r path; do
      rm -rf -- "$path"
    done < "$artifact_file"
    rm -f "$artifact_file"
    echo "Removed local generated artifacts."
    ;;
  -h|--help)
    usage
    ;;
  *)
    echo "Unknown option: $command" >&2
    usage >&2
    exit 2
    ;;
esac
