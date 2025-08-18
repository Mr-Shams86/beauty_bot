# scheduler/reminders.py
from __future__ import annotations

import datetime as dt
from typing import Dict, Tuple

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from utils.helpers import TZ, format_local_datetime
from database import get_appointments, AppointmentStatus


# Простая защита от повторных отправок в течение одной и той же минуты
# ключ: (appointment_id, "24h"/"2h", minute_dt)
_recent: Dict[Tuple[int, str, dt.datetime], float] = {}

WINDOW_SEC = 75  # сколько держим метку «уже слали» (сек)

def _floor_minute(d: dt.datetime) -> dt.datetime:
    return d.astimezone(TZ).replace(second=0, microsecond=0)

def _same_minute(a: dt.datetime, b: dt.datetime) -> bool:
    return _floor_minute(a) == _floor_minute(b)

def _prune_recent(now_ts: float) -> None:
    # чистим устаревшие метки
    to_del = [k for k, exp in _recent.items() if exp <= now_ts]
    for k in to_del:
        _recent.pop(k, None)


async def _tick(bot):
    now = dt.datetime.now(TZ)
    # целевые моменты: через 24 часа и через 2 часа от текущего момента
    targets = [
        (now + dt.timedelta(hours=24), "24h", "за 24 часа"),
        (now + dt.timedelta(hours=2),  "2h",  "за 2 часа"),
    ]

    # чистим кэш дублей
    _prune_recent(now.timestamp())

    appts = await get_appointments()  # ORM-объекты
    for a in appts:
        # напоминаем только по подтверждённым записям
        if getattr(a, "status", None) != AppointmentStatus.CONFIRMED:
            continue

        # убеждаемся, что дата aware
        if a.date.tzinfo is None:
            logger.warning("Appointment %s has naive datetime, skipping", a.id)
            continue

        svc_name = getattr(getattr(a, "service", None), "name", None) or "Услуга"
        when_str = format_local_datetime(a.date)

        for target_dt, label, human in targets:
            if _same_minute(a.date, target_dt):
                key = (a.id, label, _floor_minute(target_dt))
                if key in _recent:
                    continue  # в эту минуту уже отправляли

                try:
                    await bot.send_message(
                        a.user_id,
                        f"🔔 Напоминание {human} до визита:\n"
                        f"💇 {svc_name}\n"
                        f"📅 {when_str}"
                    )
                    # помечаем, чтобы не слать повторно в ту же минуту
                    _recent[key] = (now.timestamp() + WINDOW_SEC)
                    logger.info("Reminder sent (%s) for appointment %s", label, a.id)
                except Exception as e:
                    logger.warning("Failed to notify user %s for appt %s: %r", a.user_id, a.id, e)


def setup_scheduler(bot):
    """
    Регистрирует периодическую задачу напоминаний.
    Запуск каждую минуту, таймзона берётся из helpers.TZ.
    """
    sched = AsyncIOScheduler(timezone=str(TZ))
    # add_job с replace_existing=True — безопасно при рестартах.
    sched.add_job(
        _tick,
        trigger="interval",
        minutes=1,
        args=[bot],
        id="reminders",
        replace_existing=True,
        coalesce=True,   # если были пропуски во время сна — выполним один раз
        max_instances=1  # не пускать параллельные тики
    )
    sched.start()
    logger.info("📆 Reminder scheduler started")
