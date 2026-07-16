#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON:-python3}"

cd "$repo_root"

echo "==> Open-source readiness"
scripts/check-open-source-ready.sh

echo "==> Repository structure"
"$python_bin" scripts/check-repository-structure.py

echo "==> Publication source guardrails"
scripts/check-publication-source.sh

echo "==> Publication secret and sensitive-data scan"
"$python_bin" scripts/check-publication-secrets.py

echo "==> Reproducible development pins"
scripts/check-reproducibility.sh

echo "==> Dependency update policy"
"$python_bin" scripts/check-dependency-updates.py

echo "==> Upstream upgrade readiness"
"$python_bin" scripts/check-upstream-upgrade-readiness.py

echo "==> Shell syntax"
bash -n scripts/bootstrap-frappe-dev.sh scripts/check-open-source-ready.sh scripts/check-publication-source.sh scripts/check-reproducibility.sh scripts/local-artifacts.sh "$0"

echo "==> Developer helper smoke"
scripts/dev.sh help >/dev/null
scripts/dev.sh demo-info >/dev/null
scripts/local-artifacts.sh --count >/dev/null

echo "==> Markdown local links"
"$python_bin" scripts/check-doc-links.py

echo "==> Contract catalog"
"$python_bin" scripts/check-contract-catalog.py

echo "==> Contract lifecycle"
"$python_bin" scripts/check-contract-lifecycle.py

echo "==> Integration safety"
"$python_bin" scripts/check-integration-safety.py

echo "==> Operations readiness"
"$python_bin" scripts/check-operations-readiness.py

echo "==> AWS production IaC"
"$python_bin" scripts/check-aws-iac.py

echo "==> Service pilot readiness"
"$python_bin" scripts/check-pilot-readiness.py

echo "==> Observability readiness"
"$python_bin" scripts/check-observability-readiness.py

echo "==> Performance readiness"
"$python_bin" scripts/check-performance-readiness.py

echo "==> AI data boundary"
"$python_bin" scripts/check-ai-data-boundary.py

echo "==> AI workflow registry"
"$python_bin" scripts/check-ai-workflow-registry.py

echo "==> Tenant isolation"
"$python_bin" scripts/check-tenant-isolation.py

echo "==> Migration safety"
"$python_bin" scripts/check-migration-safety.py

echo "==> GitHub metadata"
"$python_bin" scripts/check-github-metadata.py

echo "==> CI workflow"
"$python_bin" scripts/check-ci-workflow.py

echo "==> GitHub labels"
"$python_bin" scripts/check-github-labels.py

echo "==> First public issues"
"$python_bin" scripts/check-first-public-issues.py

echo "==> MVP acceptance"
"$python_bin" scripts/check-mvp-acceptance.py

echo "==> Field-service 9/10 scorecard"
"$python_bin" scripts/check-field-service-9-scorecard.py

echo "==> Authorization matrix"
"$python_bin" scripts/check-authorization-matrix.py

echo "==> Transaction safety"
"$python_bin" scripts/check-transaction-safety.py

echo "==> Audit evidence"
"$python_bin" scripts/check-audit-evidence.py

echo "==> Fresh-clone demo"
"$python_bin" scripts/check-fresh-clone-demo.py

echo "==> Demo script"
"$python_bin" scripts/check-demo-script.py

echo "==> Release readiness manifest"
"$python_bin" scripts/check-release-readiness.py

echo "==> Release policy"
"$python_bin" scripts/check-release-policy.py

echo "==> Owner decision template"
"$python_bin" scripts/check-owner-decisions.py

echo "==> License metadata"
"$python_bin" scripts/check-license-metadata.py

echo "==> Industry pack manifest"
"$python_bin" scripts/check-industry-pack-manifest.py

echo "==> Industry pack lifecycle"
"$python_bin" scripts/check-industry-pack-lifecycle.py

echo "==> Public claims"
"$python_bin" scripts/check-public-claims.py

echo "==> Python syntax"
PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/ai-erp-pycache}" \
  "$python_bin" -m compileall -q \
  apps/ai_erp_core \
  apps/ai_erp_service \
  services/ai_control_plane/src \
  tests/contract

echo "Static quality gates passed."
echo
echo "For Docker-backed ERP checks, run the commands in docs/workflows/quality-gates.md."
