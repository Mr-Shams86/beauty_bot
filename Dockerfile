FROM python:3.12-slim

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# tzdata для таймзоны
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# зависимости
COPY requirements.txt .
RUN python -m pip install --upgrade pip wheel \
    && pip install --no-cache-dir -r requirements.txt

# код
COPY . .

# не-рут пользователь
RUN useradd -ms /bin/bash appuser
USER appuser

# скрипт запуска (миграции + бот)
COPY --chown=appuser:appuser entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# таймзона берётся из ENV TZ
ENTRYPOINT ["/entrypoint.sh"]
