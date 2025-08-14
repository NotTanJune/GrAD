# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . ./

# collect static if you use it (optional)
# RUN python manage.py collectstatic --noinput

# Gunicorn entrypoint
CMD gunicorn appmgr.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120