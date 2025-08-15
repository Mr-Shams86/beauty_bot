#!/usr/bin/env bash
set -e

# Ждём БД (простая проверка порта)
python - <<'PY'
import os, socket, time
host = os.getenv("POSTGRES_HOST", "postgres")
port = int(os.getenv("POSTGRES_PORT","5432"))
for i in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print("Postgres is up!")
            break
    except OSError:
        print("Waiting for Postgres...")
        time.sleep(2)
else:
    raise SystemExit("Postgres not available")
PY

# Миграции
alembic upgrade head

# Запуск бота
exec python bot.py
