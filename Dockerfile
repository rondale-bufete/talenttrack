# Multi-stage build. Targets:
#   (default, last stage) prod  -> what Render / Cloud Run run
#   test                        -> Python + Chromium for the pytest + Selenium suite
#   base                        -> used by the dev profile in docker-compose.yml

# ---------- Stage 1: build the React app ----------
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: Python + app code (shared by every target below) ----------
FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# ---------- Stage 3: test image (Chromium + matching chromedriver from Debian) ----------
FROM base AS test
RUN apt-get update \
 && apt-get install -y --no-install-recommends chromium chromium-driver \
 && rm -rf /var/lib/apt/lists/*
ENV CHROME_BINARY=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver
CMD ["pytest", "-q"]

# ---------- Stage 4: production image (keep this stage LAST: it is the default) ----------
FROM base AS prod
ENV DJANGO_DEBUG=false \
    PORT=8080
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput
# Run as a non-root user (who must own the folder so SQLite can write db.sqlite3)
RUN useradd --create-home appuser && chown -R appuser /app/backend && chmod +x start.sh
USER appuser
EXPOSE 8080
# start.sh: migrate -> optional demo seed -> gunicorn on $PORT
CMD ["./start.sh"]
