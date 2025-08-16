# Use Python 3.11 slim
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PYTHONPATH=/app

WORKDIR /app

# System deps (curl needed for healthcheck), libpq for psycopg
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
 && rm -rf /var/lib/apt/lists/*

# Python deps first (better cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Project files
COPY . .

# Ensure static root exists (avoid whitenoise warning if empty)
RUN mkdir -p /app/staticfiles

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck hits our Django /healthz
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/healthz || exit 1

# Gunicorn command
CMD ["sh","-lc","gunicorn appmgr.wsgi:application -b 0.0.0.0:${PORT:-8000} -w ${WEB_CONCURRENCY:-2} --timeout 180 --keep-alive 75 --access-logfile - --error-logfile -"]