#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$repo_root/infra/compose/docker-compose.dev.yml"
env_file="${AI_ERP_ENV_FILE:-$repo_root/development/.env}"

cd "$repo_root"

usage() {
  cat <<'USAGE'
Usage: scripts/dev.sh <command>

Commands:
  help                  Show this help.
  quality               Run static quality gates.
  open-source-ready     Run publishability guard in normal mode.
  release-ready         Run publishability guard in strict release mode.
  compose-config        Validate Compose using tracked .env.example copied to /tmp.
  check-local-env       Warn about unsafe or stale local development/.env values.
  local-artifacts       List ignored local generated artifacts.
  clean-local-artifacts Delete ignored local generated artifacts.
  demo-info             Print local demo URLs, roles, health hints, and next commands.
  up                    Start the local Docker development stack.
  bootstrap             Bootstrap/pin Frappe, ERPNext, and custom apps.
  bench-start           Start Frappe Bench processes in the frappe container.
  control-plane-test    Run AI control-plane unit tests in Docker.
  contract-test         Run API contract tests in Docker.
  migrate               Run Frappe migrations for the local site.
  seed-demo             Create idempotent synthetic service demo data.
  seed-rich-demo        Layer the bounded rich synthetic portfolio over the base seed.
  service-test          Run all AI ERP Service integration tests.
  performance-smoke     Run rollback-only scaled synthetic performance checks.
  e2e-test              Run local synthetic Chromium role/route smoke tests.
  demo-check            Run the Docker-backed checks that prove the MVP demo.
USAGE
}

compose() {
  docker compose --env-file "$env_file" -f "$compose_file" "$@"
}

require_local_env() {
  if [ ! -f "$env_file" ]; then
    echo "Missing local env file: $env_file" >&2
    echo "Copy development/.env.example to development/.env and change local-only secrets." >&2
    exit 1
  fi
}

check_local_env() {
  require_local_env

  local warnings=0
  if grep -Eq 'frappe/bench:|mariadb:[0-9]|redis:[0-9]|:latest' "$env_file"; then
    echo "WARN: $env_file contains tag-based image values. Prefer digest pins from development/.env.example." >&2
    warnings=$((warnings + 1))
  fi
  if ! grep -Eq '^FRAPPE_COMMIT=[0-9a-f]{40}$' "$env_file"; then
    echo "WARN: $env_file is missing a full FRAPPE_COMMIT pin." >&2
    warnings=$((warnings + 1))
  fi
  if ! grep -Eq '^ERPNEXT_COMMIT=[0-9a-f]{40}$' "$env_file"; then
    echo "WARN: $env_file is missing a full ERPNEXT_COMMIT pin." >&2
    warnings=$((warnings + 1))
  fi

  if [ "$warnings" -eq 0 ]; then
    echo "Local environment looks pinned."
  else
    echo "Local environment has $warnings warning(s); update it from development/.env.example before publishing results." >&2
  fi
}

site_name() {
  local configured_site=""
  if [ -f "$env_file" ]; then
    configured_site="$(grep -E '^SITE_NAME=' "$env_file" | tail -n 1 | cut -d= -f2- || true)"
  fi
  printf '%s' "${AI_ERP_SITE_NAME:-${configured_site:-ai-erp.localhost}}"
}

display_env_file() {
  case "$env_file" in
    "$repo_root"/*)
      printf '%s' "${env_file#"$repo_root"/}"
      ;;
    *)
      printf '%s' "custom AI_ERP_ENV_FILE path"
      ;;
  esac
}

demo_info() {
  local site
  site="$(site_name)"
  local env_label
  env_label="$(display_env_file)"
  local hosts_hint="not checked"
  if [ -r /etc/hosts ]; then
    if grep -Fq "$site" /etc/hosts; then
      hosts_hint="found ${site} in /etc/hosts"
    else
      hosts_hint="missing ${site}; add the local-only hosts entry shown above if the browser cannot resolve it"
    fi
  fi

  local env_hint="missing ${env_label}; copy development/.env.example before starting Docker"
  if [ -f "$env_file" ]; then
    env_hint="found ${env_label}; values are intentionally not printed; absolute local paths are intentionally not printed"
  fi

  local docker_hint="Docker CLI not found on PATH"
  if command -v docker >/dev/null 2>&1; then
    docker_hint="Docker CLI found; run scripts/dev.sh compose-config to validate Compose"
  fi

  local bench_hint="local bench checkout missing; run scripts/dev.sh bootstrap after the stack is up"
  if [ -d "$repo_root/development/frappe-bench" ]; then
    bench_hint="local bench checkout exists under ignored development/frappe-bench/"
  fi

  cat <<INFO
AI ERP Demo local guide

Desk URL:
  http://${site}:8000/app

If the host name does not resolve, add this local-only hosts entry:
  127.0.0.1 ${site}

Login:
  User: Administrator
  Password: read ADMIN_PASSWORD from ${env_label}
  Do not print, commit, or share local passwords.

First-run commands:
  cp development/.env.example development/.env
  scripts/dev.sh check-local-env
  scripts/dev.sh up
  scripts/dev.sh bootstrap
  scripts/dev.sh bench-start

Demo commands:
  scripts/dev.sh seed-demo
  scripts/dev.sh demo-check

Local health hints:
  Env file: ${env_hint}
  Host mapping: ${hosts_hint}
  Docker: ${docker_hint}
  Bench checkout: ${bench_hint}
  For pin warnings without printing secrets: scripts/dev.sh check-local-env

Synthetic demo users:
  service.technician@example.test
  service.manager@example.test

Important boundaries:
  - The AI control plane is internal to Docker Compose; use the ERP UI and tests
    rather than calling it from the host browser.
  - Demo data must stay synthetic.
  - AI drafts are review-only and cannot post invoices, stock, payroll,
    permissions, compliance changes, or emails.

More detail:
  docs/runbooks/local-demo.md
  docs/runbooks/demo-script.md
INFO
}

command="${1:-help}"
case "$command" in
  help|-h|--help)
    usage
    ;;
  quality)
    scripts/run-quality-gates.sh
    ;;
  open-source-ready)
    scripts/check-open-source-ready.sh
    ;;
  release-ready)
    scripts/check-open-source-ready.sh --release
    ;;
  compose-config)
    cp development/.env.example /tmp/ai-erp-ci.env
    docker compose --env-file /tmp/ai-erp-ci.env -f "$compose_file" config --quiet
    ;;
  check-local-env)
    check_local_env
    ;;
  local-artifacts)
    scripts/local-artifacts.sh
    ;;
  clean-local-artifacts)
    scripts/local-artifacts.sh --clean
    ;;
  demo-info)
    demo_info
    ;;
  up)
    require_local_env
    check_local_env
    compose up -d
    ;;
  bootstrap)
    require_local_env
    check_local_env
    compose exec --workdir /workspace frappe bash /workspace/scripts/bootstrap-frappe-dev.sh
    ;;
  bench-start)
    require_local_env
    compose exec frappe bash -lc 'cd /workspace/development/frappe-bench && bench start'
    ;;
  control-plane-test)
    require_local_env
    compose exec --workdir /workspace frappe python -m pip install ./services/ai_control_plane
    compose exec --workdir /workspace frappe python -m unittest discover -s services/ai_control_plane/tests -v
    ;;
  contract-test)
    require_local_env
    compose exec --workdir /workspace frappe python -m pip install ./services/ai_control_plane
    compose exec --workdir /workspace frappe python -m unittest discover -s tests/contract -v
    ;;
  migrate)
    require_local_env
    compose exec --workdir /workspace/development/frappe-bench frappe bench --site "$(site_name)" migrate
    ;;
  seed-demo)
    require_local_env
    compose exec \
      -e AI_ERP_LOCAL_SETUP_ALLOW=1 \
      --workdir /workspace/development/frappe-bench frappe \
      bench --site "$(site_name)" execute ai_erp_service.demo_seed.initialize_local_demo_site
    compose exec --workdir /workspace/development/frappe-bench frappe bench --site "$(site_name)" execute ai_erp_service.demo_seed.seed_service_demo
    ;;
  seed-rich-demo)
    require_local_env
    "$0" seed-demo
    compose exec --workdir /workspace/development/frappe-bench frappe bench --site "$(site_name)" execute ai_erp_service.demo_seed.seed_rich_demo
    ;;
  service-test)
    require_local_env
    compose exec --workdir /workspace/development/frappe-bench frappe bench --site "$(site_name)" run-tests --app ai_erp_service --test-category integration --failfast
    ;;
  performance-smoke)
    require_local_env
    compose exec --workdir /workspace/development/frappe-bench frappe \
      bench --site "$(site_name)" run-tests --app ai_erp_service \
      --module ai_erp_service.tests.test_performance --failfast
    compose exec \
      -e AI_ERP_PERFORMANCE_ALLOW=1 \
      -e AI_ERP_PROVIDER=template \
      --workdir /workspace/development/frappe-bench frappe \
      bench --site "$(site_name)" execute ai_erp_service.performance.run \
      --kwargs '{"scale":0.01,"samples":20,"strict":True,"allow_local":True}'
    ;;
  e2e-test)
    require_local_env
    credential_value="$(grep -E '^E2E_USER_PASSWORD=' "$env_file" | tail -n 1 | cut -d= -f2- || true)"
    playwright_image="$(grep -E '^PLAYWRIGHT_IMAGE=' "$env_file" | tail -n 1 | cut -d= -f2- || true)"
    if [ -z "$credential_value" ] || [ -z "$playwright_image" ]; then
      echo "E2E_USER_PASSWORD and PLAYWRIGHT_IMAGE are required in the local env file." >&2
      exit 1
    fi
    compose exec \
      -e AI_ERP_E2E_ALLOW=1 \
      -e AI_ERP_CONFIGURED_DEMO_ALLOW=1 \
      -e E2E_USER_PASSWORD="$credential_value" \
      --workdir /workspace/development/frappe-bench frappe \
      bench --site "$(site_name)" execute ai_erp_service.demo_seed.prepare_e2e_demo
    docker run --rm --init --ipc=host \
      --network ai-erp-dev_default \
      --volume "$repo_root:/workspace" \
      --workdir /workspace/tests/e2e \
      -e E2E_BASE_URL=http://frappe:8000 \
      -e E2E_SITE_NAME=ai-erp.localhost \
      -e E2E_USER_PASSWORD="$credential_value" \
      "$playwright_image" \
      sh -lc 'npm ci --ignore-scripts && npx playwright test'
    ;;
  demo-check)
    require_local_env
    scripts/run-quality-gates.sh
    "$0" compose-config
    "$0" control-plane-test
    "$0" contract-test
    "$0" migrate
    "$0" seed-demo
    "$0" service-test
    "$0" e2e-test
    ;;
  *)
    echo "Unknown command: $command" >&2
    usage >&2
    exit 2
    ;;
esac
