# Single-service image for Render: API + frontend in one container, no separate Celery worker.
# Local development uses docker-compose.yml with backend/Dockerfile instead.
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY frontend/ /frontend/

ENV FRONTEND_DIR=/frontend \
    UPLOADS_DIR=/app/uploads \
    GENERATED_DIR=/app/generated \
    CELERY_TASK_ALWAYS_EAGER=true

EXPOSE 8000

# Render passes the port in $PORT
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
