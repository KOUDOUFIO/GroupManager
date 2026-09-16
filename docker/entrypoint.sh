#!/usr/bin/env sh
set -e

if [ "$DB_HOST" = "db" ]; then
  echo "Waiting for Postgres..."
  until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; do
    sleep 1
  done
  echo "Postgres is ready."
fi

python manage.py migrate
python manage.py collectstatic --noinput

gunicorn groupmanager.wsgi:application --bind 0.0.0.0:8000
