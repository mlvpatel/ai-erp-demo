#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
strict=0

usage() {
  cat <<'USAGE'
Usage: scripts/check-publication-source.sh [--strict]

Checks whether local-only files that must never be published are present in the
working tree. Without --strict, findings are warnings so local development can
continue. With --strict, findings fail the command for release/archive prep.
USAGE
}

if [ "${1:-}" = "--strict" ]; then
  strict=1
elif [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
elif [ "${1:-}" != "" ]; then
  echo "Unknown option: $1" >&2
  usage >&2
  exit 2
fi

cd "$repo_root"

list_forbidden_paths() {
  find . \
    \( -path './.git' -o -path './development/frappe-bench/.git' \) -prune -o \
    \( -path './.env' -o \
       -path './.env.*' -o \
       -path './development/.env' -o \
       -path './development/frappe-bench' -o \
       -path './development/.venv' -o \
       -path './config/owner-decisions.local.json' -o \
       -path './sites' -o \
       -path './logs' -o \
       -path './private' -o \
       -path './public/assets' \
       -o -path './.terraform' \
    \) -print -prune -o \
    \( -type f \( \
       -name '*.pem' -o \
       -name '*.key' -o \
       -name '*.sql' -o \
       -name '*.sql.gz' -o \
       -name '*.dump' -o \
       -name '*.backup' -o \
       -name '*-files.tar' -o \
       -name '*-private-files.tar' \
       -o -name '*.tfstate' \
       -o -name '*.tfstate.*' \
       -o -name '*.tfvars' \
       -o -name '*.tfplan' \
    \) -print \) |
    awk '$0 != "./.env.example"' |
    awk '$0 !~ /[.]tfvars[.]example$/' |
    sort
}

forbidden_file="$(mktemp)"
list_forbidden_paths > "$forbidden_file"

if [ -s "$forbidden_file" ]; then
  if [ "$strict" -eq 1 ]; then
    cat "$forbidden_file" >&2
    rm -f "$forbidden_file"
    echo "Publication source check failed: local-only paths are present." >&2
    exit 1
  fi
  cat "$forbidden_file" >&2
  echo "WARN: local-only paths are present; do not include them in a manual source archive." >&2
fi

rm -f "$forbidden_file"

if [ "$strict" -eq 1 ]; then
  echo "Publication source check passed."
else
  echo "Publication source guardrails checked."
fi
