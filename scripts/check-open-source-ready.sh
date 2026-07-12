#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON:-python3}"
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

require_file() {
  local file="$1"
  if [ ! -f "$file" ]; then
    fail "missing required file: $file"
  fi
}

require_gitignore_pattern() {
  local pattern="$1"
  if ! grep -Fxq "$pattern" .gitignore; then
    fail ".gitignore must contain exact pattern: $pattern"
  fi
}

require_file README.md
require_file AGENTS.md
require_file ROADMAP.md
require_file BACKLOG.md
require_file CONTRIBUTING.md
require_file CODE_OF_CONDUCT.md
require_file GOVERNANCE.md
require_file SECURITY.md
require_file SUPPORT.md
require_file CHANGELOG.md
require_file .gitignore
require_file .gitattributes
require_file .github/dependabot.yml
require_file .github/ISSUE_TEMPLATE/ai_workflow.md
require_file .github/labels.json
require_file .github/repository-metadata.json
require_file .github/pull_request_template.md
require_file .github/workflows/ci.yml
require_file contracts/catalog.json
require_file scripts/check-contract-catalog.py
require_file scripts/check-contract-lifecycle.py
require_file scripts/check-integration-safety.py
require_file scripts/check-operations-readiness.py
require_file scripts/check-observability-readiness.py
require_file scripts/check-performance-readiness.py
require_file scripts/check-ai-data-boundary.py
require_file scripts/check-ai-workflow-registry.py
require_file scripts/check-tenant-isolation.py
require_file scripts/check-migration-safety.py
require_file scripts/check-dependency-updates.py
require_file scripts/check-upstream-upgrade-readiness.py
require_file scripts/check-doc-links.py
require_file scripts/check-publication-secrets.py
require_file scripts/check-github-metadata.py
require_file scripts/check-ci-workflow.py
require_file scripts/check-github-labels.py
require_file scripts/check-first-public-issues.py
require_file scripts/check-mvp-acceptance.py
require_file scripts/check-fresh-clone-demo.py
require_file scripts/check-demo-script.py
require_file scripts/check-authorization-matrix.py
require_file scripts/check-transaction-safety.py
require_file scripts/check-audit-evidence.py
require_file scripts/check-release-readiness.py
require_file scripts/check-release-policy.py
require_file scripts/check-owner-decisions.py
require_file scripts/check-license-metadata.py
require_file scripts/check-industry-pack-manifest.py
require_file scripts/check-industry-pack-lifecycle.py
require_file scripts/check-public-claims.py
require_file scripts/check-repository-structure.py
require_file scripts/local-artifacts.sh
require_file scripts/check-publication-source.sh
require_file config/industry-packs.json
require_file config/contract-lifecycle.json
require_file config/integration-safety.json
require_file config/operations-readiness.json
require_file config/observability-readiness.json
require_file config/performance-readiness.json
require_file config/repository-structure.json
require_file config/first-public-issues.json
require_file config/mvp-acceptance.json
require_file config/authorization-matrix.json
require_file config/transaction-safety.json
require_file config/audit-evidence.json
require_file config/fresh-clone-demo.json
require_file config/demo-script.json
require_file config/release-readiness.json
require_file config/release-policy.json
require_file config/industry-pack-lifecycle.json
require_file config/owner-decisions.example.json
require_file config/license-metadata.json
require_file config/ci-workflow.json
require_file config/ai-data-boundary.json
require_file config/ai-workflow-registry.json
require_file config/tenant-isolation.json
require_file config/migration-safety.json
require_file config/dependency-updates.json
require_file config/upstream-upgrade-readiness.json
require_file config/publication-secret-scan.json
require_file docs/runbooks/github-publication.md
require_file docs/runbooks/license-decision.md
require_file docs/runbooks/demo-script.md
require_file docs/runbooks/backup-restore.md
require_file docs/runbooks/incident-response.md
require_file docs/security/threat-model.md
require_file docs/security/data-classification.md
require_file docs/security/ai-workflow-review.md
require_file docs/architecture/tech-stack-2026-07.md
require_file docs/architecture/system-context-and-repository-map.md
require_file docs/architecture/system-boundaries.md
require_file docs/architecture/domain-data-model.md
require_file docs/product/public-positioning.md
require_file docs/product/requirements-traceability.md
require_file docs/discovery/open-source-erp-scan-2026-07.md
require_file docs/discovery/discovery-design-plan.md
require_file docs/discovery/service-operations-interview-guide.md
require_file docs/workflows/dependency-updates.md
require_file docs/workflows/upstream-upgrade-readiness.md
require_file docs/workflows/ai-workflow-lifecycle.md
require_file docs/workflows/tenant-isolation.md
require_file docs/workflows/migration-safety.md
require_file docs/workflows/integration-safety.md
require_file docs/workflows/operations-readiness.md
require_file docs/workflows/observability-readiness.md
require_file docs/workflows/performance-readiness.md
require_file docs/workflows/contract-lifecycle.md
require_file docs/workflows/issue-triage.md
require_file docs/workflows/release-process.md
require_file docs/workflows/industry-pack-lifecycle.md
require_file docs/workflows/authorization-and-approvals.md
require_file docs/workflows/transaction-safety.md
require_file docs/workflows/audit-evidence.md
require_file infra/observability/README.md
require_file infra/observability/alert-rules.example.yml
require_file tests/performance/README.md
require_file tests/performance/service-operations-load-profile.example.json
require_file contracts/openapi/ai-control-plane-v1.yaml
require_file contracts/events/README.md
require_file contracts/events/service-operations-v1.yaml

require_gitignore_pattern ".env"
require_gitignore_pattern ".env.*"
require_gitignore_pattern "!.env.example"
require_gitignore_pattern "*.pem"
require_gitignore_pattern "*.key"
require_gitignore_pattern "*.sql"
require_gitignore_pattern "*.sql.gz"
require_gitignore_pattern "*.dump"
require_gitignore_pattern "*.backup"
require_gitignore_pattern "*-files.tar"
require_gitignore_pattern "*-private-files.tar"
require_gitignore_pattern "__pycache__/"
require_gitignore_pattern "*.py[cod]"
require_gitignore_pattern "development/frappe-bench/"
require_gitignore_pattern "development/.env"
require_gitignore_pattern "sites/"
require_gitignore_pattern "logs/"
require_gitignore_pattern "private/"
require_gitignore_pattern "config/owner-decisions.local.json"

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

if [ -f LICENSE ]; then
  echo "Root LICENSE present."
elif [ "$strict_release" -eq 1 ]; then
  fail "root LICENSE is required for --release; see docs/adr/0005-root-license-required-before-github-publish.md"
else
  warn "root LICENSE is pending owner decision; release remains blocked by ADR-0005"
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
