# ---- Build stage ----
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements/prod.txt ./requirements/prod.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements/prod.txt && \
    pip install --no-cache-dir --prefix=/install whitenoise

# ---- Production stage ----
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_ENV=production

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

# Collect static files (whitenoise needs this)
RUN SECRET_KEY=build-placeholder python manage.py collectstatic --noinput

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/api/health/')" || exit 1

CMD gunicorn config.wsgi:application \
     --bind "0.0.0.0:${PORT:-8000}" \
     --workers 2 \
     --worker-class gthread \
     --threads 2 \
     --timeout 30 \
     --access-logfile - \
     --error-logfile -
