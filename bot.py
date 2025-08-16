from __future__ import annotations

from scheduler.reminders import setup_scheduler

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
        redis = aioredis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            socket_timeout=3,
            socket_connect_timeout=3,
        )
        await redis.ping()
        log.info(f"FSM storage: Redis {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
        return RedisStorage(
            redis=redis,
            key_builder=DefaultKeyBuilder(with_bot_id=True),  # <-- вот это
        )
    except Exception as e:
        log.warning(f"Redis недоступен, используем MemoryStorage. Причина: {e}")
        return MemoryStorage()

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    setup_scheduler(bot)
    storage = await create_storage()
    dp = Dispatcher(storage=storage)

    dp.message.middleware.register(ThrottlingMiddleware(rate=0.5))
    dp.callback_query.middleware.register(ThrottlingMiddleware(rate=0.5))

    register_client_handlers(dp)
    register_admin_handlers(dp)

    await set_bot_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)

    log.info("✅ Бот запущен. Ожидаю обновления...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        if isinstance(storage, RedisStorage):
            await storage.redis.aclose()
