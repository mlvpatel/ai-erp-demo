FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
RUN pip install --no-cache-dir .

RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid appuser --no-create-home \
        --home-dir /nonexistent --shell /usr/sbin/nologin appuser

EXPOSE 8090

USER 10001:10001

CMD ["uvicorn", "ai_erp_control_plane.app:app", "--host", "0.0.0.0", "--port", "8090"]
