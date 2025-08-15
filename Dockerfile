# Dockerfile
FROM python:3.12-slim

ENV PYTHONPATH=/app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Установим tzdata, чтобы работала таймзона
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код
COPY . .

# Скрипт запуска (миграции + бот)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Таймзона берётся из ENV TZ
ENTRYPOINT ["/entrypoint.sh"]
