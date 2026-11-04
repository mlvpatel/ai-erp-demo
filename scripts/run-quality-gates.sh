#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON:-python3}"
# Gates import scripts/_gate.py; keep its bytecode out of the local-artifact count.
export PYTHONDONTWRITEBYTECODE=1

cd "$repo_root"

echo "==> Open-source readiness"
scripts/check-open-source-ready.sh

echo "==> Repository structure"
"$python_bin" scripts/check-repository-structure.py

echo "==> Publication source guardrails"
scripts/check-publication-source.sh

echo "==> Dependency update policy"
"$python_bin" scripts/check-dependency-updates.py

echo "==> Upstream upgrade readiness"
"$python_bin" scripts/check-upstream-upgrade-readiness.py

echo "==> Shell syntax"
bash -n scripts/bootstrap-frappe-dev.sh scripts/check-open-source-ready.sh scripts/check-publication-source.sh scripts/local-artifacts.sh "$0"

echo "==> Developer helper smoke"
scripts/dev.sh help >/dev/null
scripts/dev.sh demo-info >/dev/null
scripts/local-artifacts.sh --count >/dev/null

python_gates=(
  "doc-links|Markdown local links"
  "contract-lifecycle|Contract lifecycle"
  "integration-safety|Integration safety"
  "operations-readiness|Operations readiness"
  "aws-iac|AWS production IaC"
  "pilot-readiness|Service pilot readiness"
  "observability-readiness|Observability readiness"
  "performance-readiness|Performance readiness"
  "ai-data-boundary|AI data boundary"
  "ai-workflow-registry|AI workflow registry"
  "capacity-imports|Capacity import resolution"
  "tenant-isolation|Tenant isolation"
  "migration-safety|Migration safety"
  "github-metadata|GitHub metadata"
  "ci-workflow|CI workflow"
  "github-labels|GitHub labels"
  "mvp-acceptance|MVP acceptance"
  "field-service-9-scorecard|Field-service 9/10 scorecard"
  "authorization-matrix|Authorization matrix"
  "transaction-safety|Transaction safety"
  "audit-evidence|Audit evidence"
  "fresh-clone-demo|Fresh-clone demo"
  "demo-script|Demo script"
  "demo-version|Demo Version packaging"
  "release-readiness|Release readiness manifest"
  "release-policy|Release policy"
  "owner-decisions|Owner decision template"
  "license-metadata|License metadata"
  "industry-pack-lifecycle|Industry pack lifecycle"
  "public-claims|Public claims"
)
for entry in "${python_gates[@]}"; do
  echo "==> ${entry#*|}"
  "$python_bin" "scripts/check-${entry%%|*}.py"
done

echo "==> Python syntax"
PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-./.pycache}" \
  "$python_bin" -m compileall -q \
  apps/ai_erp_core \
  apps/ai_erp_service \
  services/ai_control_plane/src \
  tests/contract

# Ruff/mypy are intentionally not part of this always-run static gate. Host
# tool presence would make the gate flip by laptop. Run them through the
# dedicated Python lint CI job, pre-commit, or:
#   python -m pip install ruff==0.14.10 && ruff check --no-cache apps/ services/

echo "Static quality gates passed."

echo
echo "For Docker-backed ERP checks, run the commands in docs/workflows/quality-gates.md."
