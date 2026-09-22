#!/usr/bin/env sh
set -e

if [ "$DB_HOST" = "db" ]; then
  echo "Waiting for Postgres..."
  until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; do
    sleep 1
  done
  echo "Postgres is ready."
fi

if [ -n "$REDIS_HOST" ]; then
  echo "Waiting for Redis..."
  until python -c "import socket,sys,os; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex((os.environ['REDIS_HOST'], int(os.environ.get('REDIS_PORT', '6379')))) == 0 else 1)" >/dev/null 2>&1; do
    sleep 1
  done
  echo "Redis is ready."
fi

python manage.py migrate
python manage.py collectstatic --noinput

exec gunicorn kotiza.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --access-logfile - \
  --error-logfile -
