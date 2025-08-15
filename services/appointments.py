# services/appointments.py (аккуратная шлифовка)
import datetime as dt
import logging

from database import (
    add_appointment as db_add,
    update_appointment as db_update_date,
    delete_appointment as db_delete,
    update_appointment_event_id as db_set_event_id,
    get_appointment_by_id,
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

async def create_appointment_and_sync(user_id: int, name: str, service: str, date: dt.datetime) -> int:
    appt_id = await db_add(user_id, name, service, date)
    log.info("Appointment %s created in DB", appt_id)

    event_id = await add_event_to_calendar(name, service, date)
    if event_id:
        await db_set_event_id(appt_id, event_id)
        log.info("Calendar event set for %s: %s", appt_id, event_id)
    else:
        log.warning("Calendar failed for appointment %s", appt_id)

    await add_appointment_to_sheet(name, service, date)
    return appt_id  # по желанию можно возвращать (appt_id, event_id)

async def reschedule_appointment_and_sync(appointment_id: int, new_date: dt.datetime) -> bool:
    appt = await get_appointment_by_id(appointment_id)
    if not appt:
        return False
    old_date = appt.date

    ok = await db_update_date(appointment_id, new_date)
    if not ok:
        return False

    if appt.event_id:
        success = await update_event_in_calendar(appt.event_id, appt.name, appt.service, new_date)
        if not success:
            log.warning("Calendar update failed for %s", appointment_id)

    updated = await update_appointment_in_sheet(appt.name, appt.service, old_date, new_date)
    if not updated:
        log.warning("Sheets update failed for %s", appointment_id)

    return True

async def delete_appointment_and_sync(appointment_id: int) -> bool:
    appt = await get_appointment_by_id(appointment_id)
    if not appt:
        return False

    if appt.event_id:
        await delete_event_from_calendar(appt.event_id)

    await delete_appointment_from_sheet(appt.name, appt.service, appt.date)
    return await db_delete(appointment_id)
