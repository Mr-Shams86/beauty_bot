# services/calendar.py
from __future__ import annotations
import asyncio
import datetime as dt
import logging
import zoneinfo
from typing import Optional

import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import GCAL_CREDENTIALS_FILE, GCAL_CALENDAR_ID

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# ---- Константы ----
TZ = zoneinfo.ZoneInfo("Asia/Tashkent")
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ---- Валидация конфигов ----
if not GCAL_CREDENTIALS_FILE or not GCAL_CALENDAR_ID:
    raise ValueError("GCAL_CREDENTIALS_FILE и GCAL_CALENDAR_ID должны быть заданы")

# ---- Инициализация клиентов (SYNC) ----
def _load_credentials():
    return service_account.Credentials.from_service_account_file(
        GCAL_CREDENTIALS_FILE, scopes=SCOPES
    )

def _get_gspread_client() -> gspread.Client:
    creds = _load_credentials()
    return gspread.authorize(creds)

def _get_calendar_service():
    creds = _load_credentials()
    # discovery build — синхронный клиент
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

# ---- Вспомогательные ----
def _fmt_sheet_dt(d: dt.datetime) -> str:
    """Формат для Google Sheets в виде 'ДД.ММ.ГГГГ ЧЧ:ММ' (локальное время)."""
    return d.astimezone(TZ).strftime("%d.%m.%Y %H:%M")

def _ensure_sheet_headers(sheet) -> None:
    headers = sheet.row_values(1)
    want = ["Name", "Service", "Date"]
    if headers != want:
        sheet.insert_row(want, 1)

# =========================
#   Google Sheets (async)
# =========================

async def add_appointment_to_sheet(name: str, service: str, date: dt.datetime) -> None:
    """Добавить строку, если её ещё нет."""
    def _sync():
        client = _get_gspread_client()
        sheet = client.open("Appointments").sheet1
        _ensure_sheet_headers(sheet)
        target = [name.strip(), service.strip(), _fmt_sheet_dt(date)]
        records = sheet.get_all_values()
        for row in records[1:]:
            if len(row) >= 3 and \
               row[0].strip().lower() == name.strip().lower() and \
               row[1].strip().lower() == service.strip().lower() and \
               row[2].strip() == target[2]:
                return  # уже есть
        sheet.append_row(target)
    await asyncio.to_thread(_sync)

async def update_appointment_in_sheet(
    name: str, service: str, old_date: dt.datetime, new_date: dt.datetime
) -> bool:
    """Найти строку по (name, service, old_date) и заменить дату."""
    def _sync():
        client = _get_gspread_client()
        sheet = client.open("Appointments").sheet1
        _ensure_sheet_headers(sheet)
        records = sheet.get_all_values()
        old_str = _fmt_sheet_dt(old_date)
        new_str = _fmt_sheet_dt(new_date)
        for i, row in enumerate(records, start=1):
            if len(row) >= 3 and \
               row[0].strip().lower() == name.strip().lower() and \
               row[1].strip().lower() == service.strip().lower() and \
               row[2].strip() == old_str:
                sheet.update_cell(i, 3, new_str)
                return True
        return False
    return await asyncio.to_thread(_sync)

async def delete_appointment_from_sheet(name: str, service: str, date: dt.datetime) -> bool:
    """Удалить строку по (name, service, date)."""
    def _sync():
        client = _get_gspread_client()
        sheet = client.open("Appointments").sheet1
        _ensure_sheet_headers(sheet)
        records = sheet.get_all_values()
        date_str = _fmt_sheet_dt(date)
        for i, row in enumerate(records, start=1):
            if len(row) >= 3 and \
               row[0].strip().lower() == name.strip().lower() and \
               row[1].strip().lower() == service.strip().lower() and \
               row[2].strip() == date_str:
                sheet.delete_rows(i)
                return True
        return False
    return await asyncio.to_thread(_sync)

# =========================
#   Google Calendar (async)
# =========================

async def add_event_to_calendar(
    name: str, service: str, date: dt.datetime, duration_hours: int = 1
) -> Optional[str]:
    """Создаёт событие и возвращает event_id."""
    def _sync():
        svc = _get_calendar_service()
        start = date.astimezone(TZ)
        end = start + dt.timedelta(hours=duration_hours)
        body = {
            "summary": f"{name} - {service}",
            "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Tashkent"},
            "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Tashkent"},
        }
        event = svc.events().insert(calendarId=GCAL_CALENDAR_ID, body=body).execute()
        return event.get("id")
    try:
        return await asyncio.to_thread(_sync)
    except Exception as e:
        logger.error("Ошибка добавления в Calendar: %s", e)
        return None

async def update_event_in_calendar(
    event_id: str, name: str, service: str, new_date: dt.datetime, duration_hours: int = 1
) -> bool:
    """Обновляет время/название события."""
    if not event_id:
        return False
    def _sync():
        svc = _get_calendar_service()
        start = new_date.astimezone(TZ)
        end = start + dt.timedelta(hours=duration_hours)
        body = {
            "summary": f"{name} - {service}",
            "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Tashkent"},
            "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Tashkent"},
        }
        svc.events().patch(calendarId=GCAL_CALENDAR_ID, eventId=event_id, body=body).execute()
        return True
    try:
        return await asyncio.to_thread(_sync)
    except Exception as e:
        logger.error("Ошибка обновления Calendar: %s", e)
        return False

async def delete_event_from_calendar(event_id: str) -> bool:
    """Удаляет событие по event_id."""
    if not event_id:
        return False
    def _sync():
        svc = _get_calendar_service()
        # проверка существования не обязательна: delete idempotent, но пусть будет мягче
        try:
            svc.events().get(calendarId=GCAL_CALENDAR_ID, eventId=event_id).execute()
        except Exception:
            return False
        svc.events().delete(calendarId=GCAL_CALENDAR_ID, eventId=event_id).execute()
        return True
    try:
        return await asyncio.to_thread(_sync)
    except Exception as e:
        logger.error("Ошибка удаления из Calendar: %s", e)
        return False
