ARG FRAPPE_BACKEND_BASE_IMAGE
FROM ${FRAPPE_BACKEND_BASE_IMAGE}

LABEL org.opencontainers.image.title="AI ERP Frappe backend" \
      org.opencontainers.image.source="https://github.com/mlvpatel/ai-erp-demo" \
      org.opencontainers.image.licenses="AGPL-3.0-only"

USER root
COPY --chown=frappe:frappe apps/ai_erp_core /home/frappe/frappe-bench/apps/ai_erp_core
COPY --chown=frappe:frappe apps/ai_erp_service /home/frappe/frappe-bench/apps/ai_erp_service
COPY --chmod=0555 infra/images/frappe/runtime.sh /opt/ai-erp/bin/runtime

USER frappe
WORKDIR /home/frappe/frappe-bench
RUN ./env/bin/pip install --no-cache-dir --no-deps \
      --editable ./apps/ai_erp_core \
      --editable ./apps/ai_erp_service

USER 1000:1000
