FROM python:3.12-slim

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# tzdata для таймзоны (TZ берём из ENV)
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- зависимости ----
COPY requirements.txt .
RUN python -m pip install --upgrade pip wheel \
    && pip install --no-cache-dir -r requirements.txt

# ---- код проекта ----
COPY . .

# ---- entrypoint (копируем под root, чтобы гарантировать доступность) ----
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# создаём пользователя без root-прав и передаём ему /app
RUN useradd -ms /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

# ---- запуск ----
ENTRYPOINT ["/entrypoint.sh"]

# ---- healthcheck ----
# используем файл, уже лежащий в /app (он попал туда через COPY . .)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python /app/healthcheck.py
