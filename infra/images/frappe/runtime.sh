#!/bin/sh
set -eu

BENCH_ROOT="${BENCH_ROOT:-/home/frappe/frappe-bench}"
cd "${BENCH_ROOT}"

ensure_apps_registry() {
  mkdir -p sites
  touch sites/apps.txt
  if [ -s sites/apps.txt ] && [ -n "$(tail -c 1 sites/apps.txt)" ]; then
    printf '\n' >>sites/apps.txt
  fi
  for app in frappe erpnext ai_erp_core ai_erp_service; do
    if ! grep -Fqx "${app}" sites/apps.txt; then
      printf '%s\n' "${app}" >>sites/apps.txt
    fi
  done
}

install_required_apps() {
  installed_apps="$(bench --site "${SITE_NAME}" list-apps)"
  for app in erpnext ai_erp_core ai_erp_service; do
    if ! printf '%s\n' "${installed_apps}" | grep -Fqx "${app}"; then
      bench --site "${SITE_NAME}" install-app "${app}"
    fi
  done
}

case "${1:-}" in
  web)
    exec ./env/bin/gunicorn --chdir=sites --bind=0.0.0.0:8000 \
      --worker-class=gthread --threads=4 --workers=2 --timeout=120 \
      --worker-tmp-dir=/tmp frappe.app:application
    ;;
  websocket)
    exec node apps/frappe/socketio.js
    ;;
  scheduler)
    exec bench schedule
    ;;
  worker-short)
    exec bench worker --queue short,default
    ;;
  worker-long)
    exec bench worker --queue long
    ;;
  configure)
    : "${SITE_NAME:?SITE_NAME is required}"
    : "${DB_HOST:?DB_HOST is required}"
    : "${DB_SSL_CA:?DB_SSL_CA is required}"
    : "${REDIS_CACHE:?REDIS_CACHE is required}"
    : "${REDIS_QUEUE:?REDIS_QUEUE is required}"
    ensure_apps_registry
    bench set-config -g db_host "${DB_HOST}"
    bench set-config -g db_port 3306
    bench set-config -g db_ssl_ca "${DB_SSL_CA}"
    bench set-config -g db_ssl_check_hostname true
    bench set-config -g redis_cache "${REDIS_CACHE}"
    bench set-config -g redis_queue "${REDIS_QUEUE}"
    bench set-config -g socketio_port 9000

    if [ ! -f "sites/${SITE_NAME}/site_config.json" ]; then
      : "${DB_ROOT_USERNAME:?DB_ROOT_USERNAME is required for a new site}"
      : "${DB_ROOT_PASSWORD:?DB_ROOT_PASSWORD is required for a new site}"
      : "${FRAPPE_ADMIN_PASSWORD:?FRAPPE_ADMIN_PASSWORD is required for a new site}"
      : "${FRAPPE_DB_NAME:?FRAPPE_DB_NAME is required for a new site}"
      : "${FRAPPE_DB_PASSWORD:?FRAPPE_DB_PASSWORD is required for a new site}"
      bench new-site "${SITE_NAME}" \
        --db-host "${DB_HOST}" \
        --db-port 3306 \
        --db-root-username "${DB_ROOT_USERNAME}" \
        --db-root-password "${DB_ROOT_PASSWORD}" \
        --db-name "${FRAPPE_DB_NAME}" \
        --db-password "${FRAPPE_DB_PASSWORD}" \
        --admin-password "${FRAPPE_ADMIN_PASSWORD}" \
        --no-mariadb-socket \
        --install-app erpnext \
        --install-app ai_erp_core \
        --install-app ai_erp_service
    fi

    install_required_apps
    bench use "${SITE_NAME}"
    ;;
  migrate)
    : "${SITE_NAME:?SITE_NAME is required}"
    exec bench --site "${SITE_NAME}" migrate
    ;;
  backup)
    : "${SITE_NAME:?SITE_NAME is required}"
    : "${BACKUP_BUCKET:?BACKUP_BUCKET is required}"
    : "${BACKUP_KMS_KEY_ARN:?BACKUP_KMS_KEY_ARN is required}"
    : "${DEPLOYMENT_ENVIRONMENT:?DEPLOYMENT_ENVIRONMENT is required}"
    BACKUP_STARTED_EPOCH="$(date +%s)"
    export BACKUP_STARTED_EPOCH
    bench --site "${SITE_NAME}" backup --with-files
    exec /opt/ai-erp/ops-venv/bin/python /opt/ai-erp/bin/backup-to-s3
    ;;
  restore)
    : "${DB_HOST:?DB_HOST is required}"
    : "${DB_SSL_CA:?DB_SSL_CA is required}"
    ensure_apps_registry
    bench set-config -g db_host "${DB_HOST}"
    bench set-config -g db_port 3306
    bench set-config -g db_ssl_ca "${DB_SSL_CA}"
    bench set-config -g db_ssl_check_hostname true
    exec /opt/ai-erp/ops-venv/bin/python /opt/ai-erp/bin/restore-drill
    ;;
  capacity)
    exec /opt/ai-erp/ops-venv/bin/python /opt/ai-erp/bin/capacity-run
    ;;
  *)
    echo "usage: runtime {web|websocket|scheduler|worker-short|worker-long|configure|migrate|backup|restore|capacity}" >&2
    exit 64
    ;;
esac
