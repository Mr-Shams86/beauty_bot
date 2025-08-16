from __future__ import annotations
from time import monotonic
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

class ThrottlingMiddleware(BaseMiddleware):
    """
    Простая защита от спама: ограничиваем частоту событий от одного пользователя.
    Не применяется, если у пользователя активно состояние FSM (бот чего-то ждёт).
    """
    def __init__(self, rate: float = 0.5):
        # минимальный интервал между событиями одного типа (сек)
        self.rate = rate
        self._last: Dict[tuple[int, str], float] = {}  # (user_id, kind) -> ts

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        # если есть активное состояние FSM — не троттлим
        state = data.get("state")
        if state and await state.get_state():
            return await handler(event, data)

        user_id = getattr(getattr(event, "from_user", None), "id", None)
        if not user_id:
            return await handler(event, data)

        kind = "cb" if isinstance(event, CallbackQuery) else "msg"
        key = (user_id, kind)

        now = monotonic()
        last = self._last.get(key, 0.0)
        if (now - last) < self.rate:
            # можно отправить мягкий ответ, если нужно:
            # if isinstance(event, Message): await event.answer("⏳ Слишком часто…")
            return  # тихо игнорируем
        self._last[key] = now
        return await handler(event, data)
