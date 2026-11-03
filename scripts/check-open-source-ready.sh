#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON:-python3}"
# check-publication-secrets.py imports scripts/_gate.py; keep its bytecode out of the artifact count below.
export PYTHONDONTWRITEBYTECODE=1
strict_release=0

if [ "${1:-}" = "--release" ]; then
  strict_release=1
elif [ "${1:-}" != "" ]; then
  echo "Usage: $0 [--release]" >&2
  exit 2
fi

cd "$repo_root"

failures=0

fail() {
  echo "FAIL: $*" >&2
  failures=$((failures + 1))
}

warn() {
  echo "WARN: $*" >&2
}

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  tracked_forbidden="$(
    git ls-files \
      '.env' '.env.*' '*.pem' '*.key' \
      '*.sql' '*.sql.gz' '*.dump' '*.backup' '*-files.tar' '*-private-files.tar' \
      '__pycache__/**' '*.pyc' '*.pyo' '*.pyd' \
      'development/.env' 'development/frappe-bench/**' \
      'sites/**' 'logs/**' 'private/**' 'public/assets/**' \
      2>/dev/null || true
  )"
  if [ -n "$tracked_forbidden" ]; then
    echo "$tracked_forbidden" >&2
    fail "forbidden local or secret-like paths are tracked"
  fi
else
  warn "not inside a Git worktree; skipped tracked-forbidden-path check"
fi

if ! "$python_bin" scripts/check-publication-secrets.py >&2; then
  fail "publication secret and sensitive-data scan failed"
fi

owner_repo_placeholder="OWNER"
owner_repo_placeholder="${owner_repo_placeholder}/REPO"
repo_url_placeholder="URL_OF_THIS"
repo_url_placeholder="${repo_url_placeholder}_REPO"
placeholder_pattern="${owner_repo_placeholder}|${repo_url_placeholder}|[$]${repo_url_placeholder}"

if find . \
  \( -path './development/frappe-bench' -o -path './.git' \) -prune -o \
  -type f \
  \( -name '*.md' -o -name '*.py' -o -name '*.js' -o -name '*.json' -o -name '*.yml' -o -name '*.yaml' -o -name '*.toml' -o -name '*.sh' -o -name '*.txt' \) \
  -print0 |
  xargs -0 grep -En "$placeholder_pattern" >&2; then
  fail "placeholder repository URL text remains"
fi

metadata_placeholder_pattern='(\[year\]|\[fullname\]|opensource@ai-erp\.example)'
if find apps services \
  -path '*/development/frappe-bench/*' -prune -o \
  -type f \
  \( -name '*.md' -o -name '*.py' -o -name '*.toml' -o -name '*.txt' \) \
  -print0 |
  xargs -0 grep -En "$metadata_placeholder_pattern" >&2; then
  if [ "$strict_release" -eq 1 ]; then
    fail "generated license/contact placeholders remain; see docs/runbooks/license-decision.md"
  else
    warn "generated license/contact placeholders remain; release remains blocked by ADR-0005"
  fi
fi

local_artifact_count="$(scripts/local-artifacts.sh --count)"
if [ "$local_artifact_count" -ne 0 ]; then
  if [ "$strict_release" -eq 1 ]; then
    fail "$local_artifact_count local generated artifact(s) remain; run scripts/local-artifacts.sh --clean before publishing an archive"
  else
    warn "$local_artifact_count local generated artifact(s) are present; run scripts/local-artifacts.sh for details"
  fi
fi

if [ "$strict_release" -eq 1 ]; then
  if ! scripts/check-publication-source.sh --strict >&2; then
    fail "publication source contains local-only paths"
  fi
fi

if [ "$failures" -ne 0 ]; then
  echo "Open-source readiness checks failed with $failures issue(s)." >&2
  exit 1
fi

echo "Open-source readiness checks passed."
