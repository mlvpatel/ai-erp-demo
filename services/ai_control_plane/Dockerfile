FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
RUN pip install --no-cache-dir .

EXPOSE 8090

CMD ["uvicorn", "ai_erp_control_plane.app:app", "--host", "0.0.0.0", "--port", "8090"]
