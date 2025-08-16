#!/usr/bin/env bash
set -euo pipefail

# ⏳ Ждём Postgres (60 попыток по 2 сек)
python - <<'PY'
import os, socket, time, sys
host = os.getenv("POSTGRES_HOST", "postgres")
port = int(os.getenv("POSTGRES_PORT", "5432"))
for i in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print("Postgres is up!")
            sys.exit(0)
    except OSError:
        print("Waiting for Postgres...")
        time.sleep(2)
print("Postgres not available", file=sys.stderr)
sys.exit(1)
PY

# 🧱 Миграции (если нечего применять — просто пройдёт)
alembic upgrade head

# ▶️ Запуск бота (foregound-процесс)
exec python bot.py
