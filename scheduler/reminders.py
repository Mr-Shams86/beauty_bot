import datetime as dt
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.helpers import TZ
from database import get_appointments
from loguru import logger

async def _tick(bot):
    now = dt.datetime.now(TZ)
    in_24h = now + dt.timedelta(hours=24)
    in_2h  = now + dt.timedelta(hours=2)

    # предполагаем, что get_appointments() возвращает ORM-объекты
    appts = await get_appointments()
    for a in appts:
        # простая проверка «ровно через 24ч / 2ч», округляя до минуты
        for target in (in_24h, in_2h):
            if abs((a.date - target).total_seconds()) < 60:
                try:
                    await bot.send_message(a.user_id, f"🔔 Напоминание: {a.service} — {a.date.astimezone(TZ):%d.%m.%Y %H:%M}")
                except Exception as e:
                    logger.warning(f"Failed to notify {a.user_id}: {e}")

def setup_scheduler(bot):
    sched = AsyncIOScheduler(timezone=str(TZ))
    sched.add_job(_tick, "interval", minutes=1, args=[bot], id="reminders", replace_existing=True)
    sched.start()
