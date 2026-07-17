ARG FRAPPE_FRONTEND_BASE_IMAGE
FROM ${FRAPPE_FRONTEND_BASE_IMAGE}

LABEL org.opencontainers.image.title="AI ERP Frappe frontend" \
      org.opencontainers.image.source="https://github.com/mlvpatel/ai-erp-demo" \
      org.opencontainers.image.licenses="AGPL-3.0-only"

USER nginx
