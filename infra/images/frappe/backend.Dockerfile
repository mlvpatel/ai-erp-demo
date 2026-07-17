ARG FRAPPE_BACKEND_BASE_IMAGE
FROM ${FRAPPE_BACKEND_BASE_IMAGE}

LABEL org.opencontainers.image.title="AI ERP Frappe backend" \
      org.opencontainers.image.source="https://github.com/mlvpatel/ai-erp-demo" \
      org.opencontainers.image.licenses="AGPL-3.0-only"

USER root
COPY infra/images/frappe/requirements-ops.lock /tmp/requirements-ops.lock
RUN python3 -m venv /opt/ai-erp/ops-venv && \
    /opt/ai-erp/ops-venv/bin/pip install --no-cache-dir --require-hashes \
      -r /tmp/requirements-ops.lock && \
    rm /tmp/requirements-ops.lock
COPY --chown=frappe:frappe apps/ai_erp_core /home/frappe/frappe-bench/apps/ai_erp_core
COPY --chown=frappe:frappe apps/ai_erp_service /home/frappe/frappe-bench/apps/ai_erp_service
COPY --chown=1000:1000 tests/performance/service-operations-load-profile.example.json /opt/ai-erp/contracts/service-operations-load-profile.json
COPY --chmod=0555 infra/images/frappe/runtime.sh /opt/ai-erp/bin/runtime
COPY --chmod=0555 infra/images/frappe/backup_to_s3.py /opt/ai-erp/bin/backup-to-s3
COPY --chmod=0555 infra/images/frappe/restore_drill.py /opt/ai-erp/bin/restore-drill
COPY --chmod=0555 infra/images/frappe/capacity_run.py /opt/ai-erp/bin/capacity-run

USER frappe
WORKDIR /home/frappe/frappe-bench
RUN ./env/bin/pip install --no-cache-dir --no-deps \
      --editable ./apps/ai_erp_core \
      --editable ./apps/ai_erp_service

USER 1000:1000
