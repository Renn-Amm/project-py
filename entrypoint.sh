#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting gunicorn on port ${PORT:-8000}..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --worker-class gthread \
    --threads 2 \
    --timeout 30 \
    --access-logfile - \
    --error-logfile -
