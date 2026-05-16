#!/usr/bin/env sh
set -eu

echo "[entrypoint] starting DB initialization and migrations"

# Run application-level initialization (creates DB/tables and seeds minimal data)
if [ -f "/app/init_db.py" ]; then
  echo "[entrypoint] running init_db.py"
  python /app/init_db.py
else
  echo "[entrypoint] init_db.py not found, skipping"
fi

echo "[entrypoint] running alembic upgrade head"
echo "[entrypoint] debug: working dir: $(pwd)"
echo "[entrypoint] debug: list /app"
ls -la /app || true
echo "[entrypoint] debug: show alembic.ini if present"
if [ -f /app/alembic.ini ]; then
  sed -n '1,120p' /app/alembic.ini || true
else
  echo "[entrypoint] debug: /app/alembic.ini not found"
fi
python -m alembic upgrade head

echo "[entrypoint] migrations complete; starting CMD"

# Exec the container command
exec "$@"
