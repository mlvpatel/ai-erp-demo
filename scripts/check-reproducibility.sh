#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_example="$repo_root/development/.env.example"
compose_file="$repo_root/infra/compose/docker-compose.dev.yml"

check_line() {
  local file="$1"
  local pattern="$2"
  local message="$3"

  if ! grep -Eq "$pattern" "$file"; then
    echo "Reproducibility check failed: $message" >&2
    exit 1
  fi
}

check_line "$env_example" '^FRAPPE_COMMIT=[0-9a-f]{40}$' "FRAPPE_COMMIT must be a full commit hash."
check_line "$env_example" '^ERPNEXT_COMMIT=[0-9a-f]{40}$' "ERPNEXT_COMMIT must be a full commit hash."
check_line "$env_example" '^MARIADB_IMAGE=[^[:space:]]+@sha256:[0-9a-f]{64}$' "MARIADB_IMAGE must be digest pinned."
check_line "$env_example" '^REDIS_IMAGE=[^[:space:]]+@sha256:[0-9a-f]{64}$' "REDIS_IMAGE must be digest pinned."
check_line "$env_example" '^FRAPPE_BENCH_IMAGE=[^[:space:]]+@sha256:[0-9a-f]{64}$' "FRAPPE_BENCH_IMAGE must be digest pinned."

if grep -En '(:latest|frappe/bench:|mariadb:[0-9]|redis:[0-9])' "$env_example" "$compose_file"; then
  echo "Reproducibility check failed: use digest-pinned images in tracked development config." >&2
  exit 1
fi

echo "Reproducibility checks passed."
