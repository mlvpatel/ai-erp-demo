#!/bin/sh
set -eu

cd /home/frappe/frappe-bench

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
    : "${REDIS_CACHE:?REDIS_CACHE is required}"
    : "${REDIS_QUEUE:?REDIS_QUEUE is required}"
    bench set-config -g db_host "${DB_HOST}"
    bench set-config -g db_port 3306
    bench set-config -g redis_cache "${REDIS_CACHE}"
    bench set-config -g redis_queue "${REDIS_QUEUE}"
    bench set-config -g socketio_port 9000
    bench use "${SITE_NAME}"
    ;;
  migrate)
    : "${SITE_NAME:?SITE_NAME is required}"
    exec bench --site "${SITE_NAME}" migrate
    ;;
  backup)
    : "${SITE_NAME:?SITE_NAME is required}"
    exec bench --site "${SITE_NAME}" backup --with-files
    ;;
  restore)
    : "${SITE_NAME:?SITE_NAME is required}"
    : "${ALLOW_RESTORE:?ALLOW_RESTORE must be explicitly set}"
    : "${RESTORE_DATABASE_FILE:?RESTORE_DATABASE_FILE is required}"
    if [ "${ALLOW_RESTORE}" != "YES" ]; then
      echo "restore requires ALLOW_RESTORE=YES" >&2
      exit 64
    fi
    exec bench --site "${SITE_NAME}" restore "${RESTORE_DATABASE_FILE}"
    ;;
  *)
    echo "usage: runtime {web|websocket|scheduler|worker-short|worker-long|configure|migrate|backup|restore}" >&2
    exit 64
    ;;
esac
