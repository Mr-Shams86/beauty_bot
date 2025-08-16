# middlewares/throttling.py
from __future__ import annotations
from time import monotonic
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

class ThrottlingMiddleware(BaseMiddleware):
    """
    Очень простая защита от спама:
    игнорируем слишком частые сообщения от одного пользователя.
    """
    def __init__(self, rate: float = 0.5):
        # минимальный интервал между событиями от одного пользователя (сек)
        self.rate = rate
        self._last: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        user_id = getattr(getattr(event, "from_user", None), "id", None)
        if not user_id:
            return await handler(event, data)

        now = monotonic()
        last = self._last.get(user_id, 0.0)
        if (now - last) < self.rate:
            return  # молча игнорируем (можно ответить “слишком часто”)
        self._last[user_id] = now
        return await handler(event, data)
