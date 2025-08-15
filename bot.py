import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
# from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder  # подключим позже
from aiogram.types import BotCommand

from config import TOKEN, DEBUG
from handlers.client import register_client_handlers
from handlers.admin import register_admin_handlers
# from redis.asyncio import Redis  # для Redis-стора в будущем


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="admin", description="Панель администратора"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    # bot properties: по умолчанию Markdown, Tashkent TZ зададим через окружение
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")  # или MarkdownV2
    )

    # Хранилище состояний: пока память, позже → RedisStorage
    storage = MemoryStorage()
    # storage = RedisStorage(
    #     Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB),
    #     key_builder=DefaultKeyBuilder(with_bot_id=True),
    # )

    dp = Dispatcher(storage=storage)

    # Регистрация хендлеров
    register_client_handlers(dp)
    register_admin_handlers(dp)

    # Команды
    await set_bot_commands(bot)

    # Чистим webhooks на всякий случай и стартуем
    await bot.delete_webhook(drop_pending_updates=True)

    if DEBUG:
        print("✅ Бот запущен. Ожидаю обновления...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
