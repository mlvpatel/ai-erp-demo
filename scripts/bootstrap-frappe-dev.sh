#!/usr/bin/env bash
set -euo pipefail

workspace=/workspace
development_dir="$workspace/development"
bench_dir="$development_dir/frappe-bench"
apps_json="$development_dir/apps.json"

: "${DB_ROOT_PASSWORD:?Set DB_ROOT_PASSWORD in development/.env}"
: "${ADMIN_PASSWORD:?Set ADMIN_PASSWORD in development/.env}"
: "${SITE_NAME:=ai-erp.localhost}"
: "${FRAPPE_BRANCH:=version-16}"
: "${FRAPPE_COMMIT:=7699c7feefac77a36853d3a955d9b6b53552f55e}"
: "${ERPNEXT_COMMIT:=d1d3b241ae7bc21d18cf830a4bacd568e21a2a19}"

pin_app_commit() {
  local app_name="$1"
  local target_commit="$2"
  local app_dir="apps/$app_name"

  if [ -z "$target_commit" ] || [ ! -d "$app_dir/.git" ]; then
    return
  fi

  local current_commit
  current_commit="$(git -C "$app_dir" rev-parse HEAD)"
  if [ "$current_commit" = "$target_commit" ]; then
    echo "$app_name already pinned to $target_commit"
    return
  fi

  if ! git -C "$app_dir" diff --quiet || ! git -C "$app_dir" diff --cached --quiet; then
    echo "Cannot pin $app_name to $target_commit because $app_dir has local changes." >&2
    echo "Commit, stash, or remove those changes, then rerun this script." >&2
    exit 1
  fi

  git -C "$app_dir" fetch origin "$target_commit"
  git -C "$app_dir" checkout --detach "$target_commit"
  echo "$app_name pinned to $target_commit"
}

ensure_local_app() {
  local app_name="$1"
  local source_dir="$workspace/apps/$app_name"
  local target_dir="apps/$app_name"

  if [ ! -d "$source_dir" ]; then
    echo "Missing local app source: $source_dir" >&2
    exit 1
  fi

  if [ -L "$target_dir" ]; then
    local current_target
    current_target="$(readlink "$target_dir")"
    if [ "$current_target" != "$source_dir" ]; then
      echo "Refusing to replace $target_dir; it points to $current_target" >&2
      exit 1
    fi
  elif [ -e "$target_dir" ]; then
    echo "Refusing to replace existing non-symlink app path: $target_dir" >&2
    exit 1
  else
    ln -s "$source_dir" "$target_dir"
    echo "Linked $app_name to $source_dir"
  fi

  "$bench_dir/env/bin/python" -m pip install --no-deps -e "$target_dir"
}

ensure_site_app() {
  local app_name="$1"

  if bench --site "$SITE_NAME" list-apps | grep -Eq "^${app_name}([[:space:]]|$)"; then
    echo "$app_name already installed on $SITE_NAME"
    return
  fi

  bench --site "$SITE_NAME" install-app "$app_name"
}

cd "$development_dir"

if [ ! -d "$bench_dir" ]; then
  bench init \
    --skip-redis-config-generation \
    --frappe-branch "$FRAPPE_BRANCH" \
    --apps_path "$apps_json" \
    frappe-bench
fi

cd "$bench_dir"
pin_app_commit frappe "$FRAPPE_COMMIT"
pin_app_commit erpnext "$ERPNEXT_COMMIT"
ensure_local_app ai_erp_core
ensure_local_app ai_erp_service

bench set-config -g db_host mariadb
bench set-config -g redis_cache redis://redis-cache:6379
bench set-config -g redis_queue redis://redis-queue:6379
bench set-config -g redis_socketio redis://redis-queue:6379
bench set-config -gp developer_mode 1

if [ ! -d "sites/$SITE_NAME" ]; then
  bench new-site \
    --db-root-username root \
    --db-host mariadb \
    --db-type mariadb \
    --mariadb-user-host-login-scope=% \
    --db-root-password "$DB_ROOT_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" \
    --install-app erpnext \
    "$SITE_NAME"
fi

ensure_site_app ai_erp_core
ensure_site_app ai_erp_service

bench --site "$SITE_NAME" list-apps
