#!/bin/sh
# Container entrypoint: prepare the database, then start the web server.
set -e

python manage.py migrate --noinput

# On free hosts without a real database, the SQLite file is wiped on every restart,
# so reseed demo data whenever the database is empty.
if [ "${SEED_DEMO:-false}" = "true" ]; then
  python manage.py seed_demo --if-empty
fi

exec gunicorn config.wsgi:application --bind ":${PORT:-8080}" --workers 2 --threads 8 --timeout 120
