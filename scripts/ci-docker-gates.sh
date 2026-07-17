#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="/tmp/ai-erp-ci.env"
compose_file="${repo_root}/infra/compose/docker-compose.dev.yml"

cd "${repo_root}"
cp development/.env.example "${env_file}"
export AI_ERP_ENV_FILE="${env_file}"

compose() {
  docker compose --env-file "${env_file}" -f "${compose_file}" "$@"
}

cleanup() {
  compose ps || true
  compose down --volumes --remove-orphans || true
}
trap cleanup EXIT

scripts/dev.sh compose-config
scripts/dev.sh up
compose exec -u root frappe chown -R frappe:frappe \
  /workspace/development \
  /workspace/apps \
  /workspace/services/ai_control_plane
scripts/dev.sh bootstrap
compose exec --workdir /workspace/development/frappe-bench frappe \
  bench --site ai-erp.localhost set-config allow_tests true
compose exec -d --workdir /workspace/development/frappe-bench frappe bench start

ready=0
for _attempt in $(seq 1 120); do
  if compose exec -T frappe python -c \
    "from urllib.request import Request,urlopen; urlopen(Request('http://127.0.0.1:8000/api/method/ping',headers={'Host':'ai-erp.localhost'}),timeout=2)" \
    >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [ "${ready}" != 1 ]; then
  echo "Frappe did not become healthy within 240 seconds." >&2
  exit 1
fi

scripts/dev.sh control-plane-test
scripts/dev.sh contract-test
scripts/dev.sh migrate
scripts/dev.sh seed-demo
compose exec --workdir /workspace/development/frappe-bench frappe \
  bench --site ai-erp.localhost run-tests --app ai_erp_core \
  --test-category integration --failfast
scripts/dev.sh service-test
scripts/dev.sh performance-smoke
scripts/dev.sh e2e-test
