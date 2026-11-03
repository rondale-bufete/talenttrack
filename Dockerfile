# ---------- Stage 1: build the React app ----------
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: Python runtime ----------
# Multi-stage build: Node and node_modules never reach the final image, keeping it small.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=false \
    PORT=8080

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

# Run as a non-root user
RUN useradd --create-home appuser
USER appuser

# Cloud Run sends traffic to $PORT. Threads per worker handle concurrent I/O-bound requests.
CMD exec gunicorn config.wsgi:application --bind :$PORT --workers 2 --threads 8 --timeout 120
