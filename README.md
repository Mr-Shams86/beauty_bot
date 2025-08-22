## 💇‍♀️ Telegram Beauty Bot

## 🌟 Описание проекта

**Телеграм-бот для онлайн-записи клиентов на стрижки, укладки и другие бьюти-услуги с интеграцией Google Calendar. Подходит как для салона, так и для частного мастера.**

## 📌 Возможности

✅ Запись клиента через пошаговую форму (имя → телефон → услуга → дата/время)

✅ Проверка корректности номера телефона (формат +998XXXXXXXXX)

✅ Выбор услуги через инлайн-кнопки (стрижка, укладка, окрашивание, брови и др.)

✅ Автоматическая проверка занятости и исключение конфликтов времени

✅ Подтверждение или отклонение записи мастером

✅ Автоматическое уведомление клиента о статусе

✅ Интеграция с Google Календарём (записи появляются в календаре мастера)

✅ Возможность изменить (перенести) или отменить запись клиентом

✅ Подробное уведомление мастеру: имя, телефон, услуга, дата/время

✅ Панель администратора для управления записями

🔜 Отправка напоминаний клиенту (24ч / 2ч до визита)

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

**Команда	        Описание**
- /start	        Начало работы
- /add_appointment	Добавить запись
- /appointments	    Посмотреть все записи (только админ)
- /get_id	        Узнать свой Telegram ID


## 📂 Структура проекта

```
📦 beauty_bot
.
├── alembic/ 🗂️ Миграции базы данных
│ ├── env.py ⚙️ Настройка Alembic окружения
│ ├── script.py.mako 📜 Шаблон для генерации миграций
│ └── versions/ 📜 Скрипты миграций
│ ├── 0001_create_appointments.py 🏗️ Создание таблицы записей
│ ├── 0002_add_users_and_services.py ➕ Таблицы пользователей и услуг
│ ├── 0003_make_appointments_name_nullable.py ✏ Поле name nullable
│ ├── 0004_add_phone_to_users.py 📞 Добавление телефона в users
│ └── f4f775f37abe_make_appointments_name_nullable_indexes_.py ⚡ Индексы
│
├── alembic.ini ⚙️ Конфигурация Alembic
├── bot.py 🤖 Точка входа для Telegram-бота
├── config.py 🔧 Конфигурация проекта (переменные окружения)
├── database.py 🗄️ Модели и функции работы с БД
├── docker-compose.yml 🐳 Docker Compose для запуска сервиса
├── Dockerfile 📦 Docker-образ приложения
├── entrypoint.sh 🚀 Скрипт запуска и применения миграций
│
├── handlers/ 🎮 Обработчики команд
│ ├── admin.py 👨‍💼 Логика администратора
│ └── client.py 🙋 Логика клиента (записи, просмотр)
│
├── healthcheck.py 🩺 Проверка состояния сервиса
├── keyboards.py 🎹 Inline/Reply клавиатуры
│
├── middlewares/ 🛡️ Middleware
│ └── throttling.py ⏱️ Ограничение спама
│
├── README.md 📘 Документация проекта
├── requirements.txt 📋 Зависимости Python
│
├── scheduler/ ⏰ Планировщик задач
│ └── reminders.py 🔔 Отправка напоминаний
│
├── secrets/ 🔐 Секреты и ключи
│ └── gcal-service-account.json 📄 Ключ сервисного аккаунта Google
│
├── services/ 🛠️ Сервисы и бизнес-логика
│ ├── appointments.py 📅 Управление записями
│ └── calendar.py 📆 Интеграция с Google Calendar
│
├── structure.txt 📝 Чистая структура проекта
├── Task 📄 Дополнительные заметки/таски
│
└── utils/ 🔧 Вспомогательные функции
├── helpers.py 🛠️ Парсинг дат, таймзона и т.д.
└── logging.py 🪵 Настройка логирования


```

🔮 В планах

⏱ Проверка рабочего времени мастера (is_in_working_hours)

🔔 Напоминания клиентам за 24ч и 2ч до записи

🌍 Мультиязычность (RU / UZ / EN)
