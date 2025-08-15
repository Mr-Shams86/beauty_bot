# 💇‍♀️ Telegram Beauty Bot

## 🌟 **Описание проекта**

## **Телеграм-бот для онлайн-записи клиентов на стрижки, укладки и другие бьюти-услуги с интеграцией Google Calendar, Подходит как для салона, так и для частного мастера.**

## 📌 Возможности

    ✅ Выбор услуги (стрижка, укладка, окрашивание, брови и др.)

    ✅ Выбор даты и времени записи

    ✅ Подтверждение или отклонение записи мастером

    ✅ Автоматическое уведомление клиента

    ✅ Интеграция с Google Календарём (записи появляются в календаре мастера)

    ✅ Возможность изменить или отменить запись

    ✅ Отправка напоминаний клиенту

    ✅ Панель администратора для управления записями

---

## 🛠 Стек технологий

-    Python 3.10+

-    Aiogram 3.x

-    PostgreSQL — хранение записей

-    SQLAlchemy + Alembic — ORM и миграции

-    Redis — для FSM (машина состояний) и кеша

-    Docker + docker-compose — развёртывание

-    Google Calendar API — синхронизация расписания

---

## 🚀 Установка и запуск

1. **Клонировать репозиторий**

- git clone https://github.com/Mr-Shams86/beauty_bot.git
- cd beauty_bot

2. **Создать .env на основе .env.example**

- BOT_TOKEN=your_bot_token_here
- ADMIN_ID=your_admin_id_here

- TZ=Asia/Tashkent
- DEBUG=True

- POSTGRES_HOST=postgres
- POSTGRES_PORT=5432
- POSTGRES_DB=beautybot
- POSTGRES_USER=beautybot
- POSTGRES_PASSWORD=supersecret
- DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

- REDIS_HOST=redis
- REDIS_PORT=6379
- REDIS_DB=0

- GCAL_CALENDAR_ID=your_calendar_id_here

3. **Запустить через Docker**

- docker compose up -d

4. **Применить миграции базы данных**

- docker compose exec bot alembic upgrade head

## 📖 Команды бота

- Команда	Описание
- /start	Начало работы
- /add_appointment	Добавить запись
- /appointments	Посмотреть все записи (только админ)
- /get_id	Узнать свой Telegram ID

---

## 📂 Структура проекта

```
📦 beauty_bot
.
├── 📁 alembic — 📜 миграции базы данных (Alembic)  
│   ├── env.py — ⚙️ настройки Alembic  
│   └── 📁 versions — 🗂 история миграций  
│       └── 0001_create_appointments.py — 🏗 создание таблицы записей  
│
├── alembic.ini — ⚙️ конфигурация Alembic  
├── bot.py — 🚀 точка входа бота  
├── config.py — 🔧 конфигурация проекта (.env)  
├── database.py — 🗄 подключение к PostgreSQL  
├── docker-compose.yml — 🐳 конфигурация Docker Compose  
├── Dockerfile — 📦 образ Docker для бота  
├── entrypoint.sh — ▶️ скрипт запуска контейнера  
│
├── 📁 handlers — 🎯 обработчики команд и сообщений  
│   ├── admin.py — 🛠 панель администратора  
│   └── client.py — 💬 логика для пользователей  
│
├── keyboards.py — ⌨️ кнопки (Inline/Reply)  
├── README.md — 📖 описание проекта  
├── requirements.txt — 📋 зависимости Python  
│
├── 📁 secrets — 🔒 секреты (не вносятся в Git)  
│   └── gcal-service-account.json — 🔑 ключ для Google Calendar API  
│
├── 📁 services — 🛎 работа с внешними сервисами  
│   ├── appointments.py — 📅 управление записями  
│   └── calendar.py — 📆 интеграция с Google Calendar  
│
├── structure.txt — 📄 описание структуры (локально)  
│
└── 📁 utils — 🛠 вспомогательные утилиты  
    └── helpers.py — 🧩 функции-помощники  

```
---

## 🔗 Ссылки

- [GitHub репозиторий](https://github.com/Mr-Shams86/beauty_bot)

## 📢 **Контакты**

- **Email**: sammertime763@gmail.com

- **Telegram**: [Mr_Shams_1986](https://t.me/Mr_Shams_1986)

---

## 📜 Лицензия

## MIT — используй и дорабатывай свободно.
