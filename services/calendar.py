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
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import GCAL_CREDENTIALS_FILE, GCAL_CALENDAR_ID

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# ---- Константы ----
TZ = zoneinfo.ZoneInfo("Asia/Tashkent")

# Разносим скопы по сервисам (быстрее и чуть безопаснее)
SCOPES_CAL = ["https://www.googleapis.com/auth/calendar"]
SCOPES_SHEETS = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ---- Валидация конфигов ----
if not GCAL_CREDENTIALS_FILE or not GCAL_CALENDAR_ID:
    raise ValueError("GCAL_CREDENTIALS_FILE и GCAL_CALENDAR_ID должны быть заданы")

# ---- Инициализация клиентов (SYNC) ----
def _calendar_service_sync():
    creds = service_account.Credentials.from_service_account_file(
        GCAL_CREDENTIALS_FILE, scopes=SCOPES_CAL
    )
    # discovery build — синхронный клиент
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

def _gspread_client_sync() -> gspread.Client:
    creds = service_account.Credentials.from_service_account_file(
        GCAL_CREDENTIALS_FILE, scopes=SCOPES_SHEETS
    )
    return gspread.authorize(creds)

def _ensure_sheet_headers(sheet) -> None:
    headers = sheet.row_values(1)
    want = ["Name", "Service", "Date"]
    if headers != want:
        sheet.insert_row(want, 1)

def _fmt_sheet_dt(d: dt.datetime) -> str:
    """Локальный формат для Google Sheets: 'ДД.ММ.ГГГГ ЧЧ:ММ'."""
    return d.astimezone(TZ).strftime("%d.%m.%Y %H:%M")

# =========================
#   Google Sheets (async)
# =========================

async def add_appointment_to_sheet(name: str, service: str, date: dt.datetime) -> None:
    """Добавить строку, если её ещё нет."""
    def _sync():
        client = _gspread_client_sync()
        sheet = client.open("Appointments").sheet1
        _ensure_sheet_headers(sheet)
        target = [name.strip(), service.strip(), _fmt_sheet_dt(date)]
        records = sheet.get_all_values()
        for row in records[1:]:
            if (
                len(row) >= 3
                and row[0].strip().lower() == name.strip().lower()
                and row[1].strip().lower() == service.strip().lower()
                and row[2].strip() == target[2]
            ):
                return  # уже есть
        sheet.append_row(target)
    await asyncio.to_thread(_sync)

async def update_appointment_in_sheet(
    name: str, service: str, old_date: dt.datetime, new_date: dt.datetime
) -> bool:
    """Найти строку по (name, service, old_date) и заменить дату."""
    def _sync():
        client = _gspread_client_sync()
        sheet = client.open("Appointments").sheet1
        _ensure_sheet_headers(sheet)
        records = sheet.get_all_values()
        old_str = _fmt_sheet_dt(old_date)
        new_str = _fmt_sheet_dt(new_date)
        for i, row in enumerate(records, start=1):
            if (
                len(row) >= 3
                and row[0].strip().lower() == name.strip().lower()
                and row[1].strip().lower() == service.strip().lower()
                and row[2].strip() == old_str
            ):
                sheet.update_cell(i, 3, new_str)
                return True
        return False
    return await asyncio.to_thread(_sync)

async def delete_appointment_from_sheet(name: str, service: str, date: dt.datetime) -> bool:
    """Удалить строку по (name, service, date)."""
    def _sync():
        client = _gspread_client_sync()
        sheet = client.open("Appointments").sheet1
        _ensure_sheet_headers(sheet)
        records = sheet.get_all_values()
        date_str = _fmt_sheet_dt(date)
        for i, row in enumerate(records, start=1):
            if (
                len(row) >= 3
                and row[0].strip().lower() == name.strip().lower()
                and row[1].strip().lower() == service.strip().lower()
                and row[2].strip() == date_str
            ):
                sheet.delete_rows(i)
                return True
        return False
    return await asyncio.to_thread(_sync)

# =========================
#   Google Calendar (async)
# =========================
# Добавляем ретраи: если HttpError/сетевой обрыв — повторяем с экспоненциальной паузой.

@retry(
    retry=retry_if_exception_type((HttpError, ConnectionError, TimeoutError)),
    wait=wait_exponential(multiplier=0.8, min=1, max=10),
    stop=stop_after_attempt(4),
)
async def add_event_to_calendar(
    name: str, service: str, date: dt.datetime, duration_hours: int = 1
) -> Optional[str]:
    """Создаёт событие и возвращает event_id."""
    assert date.tzinfo is not None, "date должен быть timezone-aware"
    def _sync():
        svc = _calendar_service_sync()
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

@retry(
    retry=retry_if_exception_type((HttpError, ConnectionError, TimeoutError)),
    wait=wait_exponential(multiplier=0.8, min=1, max=10),
    stop=stop_after_attempt(4),
)
async def update_event_in_calendar(
    event_id: str, name: str, service: str, new_date: dt.datetime, duration_hours: int = 1
) -> bool:
    """Обновляет время/название события."""
    if not event_id:
        return False
    assert new_date.tzinfo is not None
    def _sync():
        svc = _calendar_service_sync()
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

@retry(
    retry=retry_if_exception_type((HttpError, ConnectionError, TimeoutError)),
    wait=wait_exponential(multiplier=0.8, min=1, max=10),
    stop=stop_after_attempt(4),
)
async def delete_event_from_calendar(event_id: str) -> bool:
    """Удаляет событие по event_id. 404 считаем «уже удалено»."""
    if not event_id:
        return False
    def _sync():
        svc = _calendar_service_sync()
        try:
            svc.events().delete(calendarId=GCAL_CALENDAR_ID, eventId=event_id).execute()
            return True
        except HttpError as e:
            # Если событие уже отсутствует (например, 404) — считаем, что цель достигнута
            if e.resp is not None and getattr(e.resp, "status", None) == 404:
                return True
            raise
    try:
        return await asyncio.to_thread(_sync)
    except Exception as e:
        logger.error("Ошибка удаления из Calendar: %s", e)
        return False
