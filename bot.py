# bot.py
from __future__ import annotations
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

# FSM storages
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
import redis.asyncio as aioredis

# наше
from config import TOKEN, DEBUG, REDIS_HOST, REDIS_PORT, REDIS_DB
from handlers.client import register_client_handlers
from handlers.admin import register_admin_handlers
from middlewares.throttling import ThrottlingMiddleware
from utils.logging import setup_logging

log = setup_logging(DEBUG)


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="admin", description="Панель администратора"),
    ]
    await bot.set_my_commands(commands)


async def create_storage():
    """Пробуем Redis, если недоступен — падаем на MemoryStorage."""
    try:
        redis = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        # лёгкая проверка соединения
        await redis.ping()
        log.info(f"FSM storage: Redis {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
        return RedisStorage(redis=redis, key_builder=DefaultKeyBuilder(with_destiny=True))
    except Exception as e:
        log.warning(f"Redis недоступен, используем MemoryStorage. Причина: {e}")
        return MemoryStorage()


async def main() -> None:
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),  # или "MarkdownV2"
    )

    storage = await create_storage()
    dp = Dispatcher(storage=storage)

    # анти-спам (игнор слишком частых событий)
    dp.message.middleware.register(ThrottlingMiddleware(rate=0.5))
    dp.callback_query.middleware.register(ThrottlingMiddleware(rate=0.5))

    # регистрируем хендлеры
    register_client_handlers(dp)
    register_admin_handlers(dp)

    # команды и старт
    await set_bot_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)

    log.info("✅ Бот запущен. Ожидаю обновления...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
