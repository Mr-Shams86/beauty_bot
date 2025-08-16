## 💇‍♀️ Telegram Beauty Bot

## 🌟 Описание проекта

**Телеграм-бот для онлайн-записи клиентов на стрижки, укладки и другие бьюти-услуги с интеграцией Google Calendar. Подходит как для салона, так и для частного мастера.**

## 📌 Возможности

    ✅ Выбор услуги (стрижка, укладка, окрашивание, брови и др.)

    ✅ Выбор даты и времени записи

    ✅ Подтверждение или отклонение записи мастером

    ✅ Автоматическое уведомление клиента

    ✅ Интеграция с Google Календарём (записи появляются в календаре мастера)

    ✅ Возможность изменить или отменить запись

    ✅ Отправка напоминаний клиенту

    ✅ Панель администратора для управления записями

## 🛠 Стек технологий

-    Python 3.10+

-    Aiogram 3.x

-    PostgreSQL — хранение записей

-    SQLAlchemy + Alembic — ORM и миграции

-    Redis — FSM (машина состояний) и кеш

-    Docker + docker-compose — развёртывание

-    Google Calendar API — синхронизация расписания

## 🚀 Deployment & Run (Docker)

1) Подготовка окружения

# клонируем репозиторий

- git clone https://github.com/Mr-Shams86/beauty_bot.git
- cd beauty_bot

# создаём .env на основе примера
- cp .env.example .env

# отредактируй .env: BOT_TOKEN, ADMIN_ID, GCAL_CALENDAR_ID и т.д.

# поместить ключ сервис-аккаунта
- mkdir -p secrets

# файл должен называться gcal-service-account.json

# и лежать в ./secrets/gcal-service-account.json

2) Сборка и запуск

# полная пересборка образа (после изменения зависимостей)
- docker-compose build --no-cache

# запуск всех сервисов
- docker-compose up -d

3) Применение миграций

- Миграции обычно запускаются автоматически в entrypoint.sh, но можно вручную:

- docker-compose exec bot alembic upgrade head

4) Логи и управление

# смотреть логи бота
- docker-compose logs -f bot

# перезапустить только бота
- docker-compose restart bot

# остановить все сервисы
- docker-compose down

## 📖 Команды бота

**Команда	Описание**
- /start	Начало работы
- /add_appointment	Добавить запись
- /appointments	Посмотреть все записи (только админ)
- /get_id	Узнать свой Telegram ID


## 📂 Структура проекта

```
📦 beauty_bot
.
├── alembic/                     🗂️ Миграции базы данных
│   ├── env.py                   ⚙️ Настройка Alembic окружения
│   └── versions/                📜 Скрипты миграций
│       └── 0001_create_appointments.py  🏗️ Первая миграция (создание таблицы записей)
│
├── alembic.ini                  ⚙️ Конфигурация Alembic
├── bot.py                       🤖 Точка входа для Telegram-бота
├── config.py                    🔧 Конфигурация проекта (env, токены и т.д.)
├── database.py                  🗄️ Подключение к базе данных
├── docker-compose.yml           🐳 Docker Compose для запуска сервиса
├── Dockerfile                   📦 Образ для контейнера
├── entrypoint.sh                 🚀 Скрипт инициализации/старта
│
├── handlers/                    🎮 Обработчики команд и логики бота
│   ├── admin.py                 👨‍💼 Логика для администратора
│   └── client.py                🙋 Логика для клиента (запись, просмотр)
│
├── healthcheck.py                🩺 Проверка состояния сервиса
├── keyboards.py                  🎹 Клавиатуры (inline и reply)
│
├── middlewares/                 🛡️ Промежуточные слои
│   └── throttling.py            ⏱️ Анти-спам middleware
│
├── README.md                    📘 Документация проекта
├── requirements.txt             📋 Зависимости проекта
│
├── scheduler/                   ⏰ Планировщик задач
│   └── reminders.py             🔔 Отправка напоминаний
│
├── secrets/                     🔐 Секреты и ключи
│   └── gcal-service-account.json 📄 Сервисный аккаунт Google Calendar
│
├── services/                    🛠️ Сервисы и бизнес-логика
│   ├── appointments.py          📅 Управление записями
│   └── calendar.py              📆 Интеграция с Google Calendar
│
├── structure.txt                 📝 Текущая структура проекта
│
└── utils/                       🔧 Утилиты и вспомогательные функции
    ├── helpers.py               🛠️ Вспомогательные функции
    └── logging.py               🪵 Настройка логирования


```
