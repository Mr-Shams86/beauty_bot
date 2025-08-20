# services/appointments.py
from __future__ import annotations

import math
import datetime as dt
import logging

from database import (
    add_appointment as db_add,                  # (user_id: int, service_id: int, date: dt) -> int
    update_appointment as db_update_date,
    delete_appointment as db_delete,
    update_appointment_event_id as db_set_event_id,
    get_appointment_by_id,
    get_service_by_id,
    has_time_conflict,
)
from services.calendar import (
    add_event_to_calendar,
    update_event_in_calendar,
    delete_event_from_calendar,
    add_appointment_to_sheet,
    update_appointment_in_sheet,
    delete_appointment_from_sheet,
)

log = logging.getLogger(__name__)


def _hours_from_minutes(minutes: int) -> int:
    """Google Calendar helper: округляем вверх до целых часов (минимум 1)."""
    minutes = minutes or 60
    return max(1, math.ceil(minutes / 60))


async def create_appointment_and_sync(
    user_id: int,            # telegram_id
    user_name: str,          # имя клиента (для красивых сообщений/Sheets)
    service_id: int,
    date: dt.datetime,
) -> int:
    
    # валидация имени
    user_name = user_name.strip()
    if not user_name:
        raise ValueError("Укажите имя")
    
    # валидация времени
    if date.tzinfo is None:
        raise ValueError("date должен быть timezone-aware")
    if date < dt.datetime.now(date.tzinfo):
        raise ValueError("нельзя бронировать прошедшее время")

    svc = await get_service_by_id(service_id)
    if not svc:
        raise ValueError("Service not found")


    # конфликт слотов
    if await has_time_conflict(date, svc.duration_min):
        raise ValueError("Этот слот уже занят")

    # БД
    appt_id = await db_add(user_id=user_id, service_id=service_id, date=date, name=user_name)
    log.info("Appointment %s created in DB", appt_id)

    # Calendar
    duration_h = _hours_from_minutes(getattr(svc, "duration_min", 60))
    event_id = await add_event_to_calendar(user_name, service_name, date, duration_hours=duration_h)
    if event_id:
        await db_set_event_id(appt_id, event_id)
        log.info("Calendar event set for %s: %s", appt_id, event_id)
    else:
        log.warning("Calendar failed for appointment %s", appt_id)

    # Sheets
    await add_appointment_to_sheet(user_name, service_name, date)


    return appt_id


async def reschedule_appointment_and_sync(
    appointment_id: int,
    new_date: dt.datetime,
) -> bool:
    if new_date.tzinfo is None:
        raise ValueError("new_date должен быть timezone-aware")
    if new_date < dt.datetime.now(new_date.tzinfo):
        raise ValueError("нельзя переносить в прошлое")

    appt = await get_appointment_by_id(appointment_id)
    if not appt:
        return False

    # тянем услугу и имя клиента
    svc = await get_service_by_id(appt.service_id) if appt.service_id else None
    service_name = getattr(svc, "name", "Услуга")
    duration_min = getattr(svc, "duration_min", appt.duration_min or 60)
    user_name = getattr(appt, "name", "Клиент")

    # проверка конфликта
    if await has_time_conflict(new_date, duration_min, exclude_id=appointment_id):
        raise ValueError("Этот слот уже занят")

    old_date = appt.date

    # БД
    ok = await db_update_date(appointment_id, new_date)
    if not ok:
        return False

    # Calendar
    if appt.event_id:
        duration_h = _hours_from_minutes(duration_min)
        success = await update_event_in_calendar(appt.event_id, user_name, service_name, new_date, duration_hours=duration_h)
        if not success:
            log.warning("Calendar update failed for %s", appointment_id)

    # Sheets
    updated = await update_appointment_in_sheet(user_name, service_name, old_date, new_date)
    if not updated:
        log.warning("Sheets update failed for %s", appointment_id)

    return True


async def delete_appointment_and_sync(appointment_id: int) -> bool:
    appt = await get_appointment_by_id(appointment_id)
    if not appt:
        return False

    svc = await get_service_by_id(appt.service_id) if appt.service_id else None
    service_name = getattr(svc, "name", "Услуга")
    user_name = getattr(appt, "name", "Клиент")

    # Calendar
    if appt.event_id:
        _ = await delete_event_from_calendar(appt.event_id)

    # Sheets
    await delete_appointment_from_sheet(user_name, service_name, appt.date)

    # DB
    return await db_delete(appointment_id)
