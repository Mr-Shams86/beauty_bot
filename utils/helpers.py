# utils/helpers.py
from __future__ import annotations
import datetime as dt
import re
import zoneinfo

TZ = zoneinfo.ZoneInfo("Asia/Tashkent")

def parse_local_datetime(s: str) -> dt.datetime:
    """
    Принимает строку 'ДД.ММ.ГГГГ ЧЧ:ММ' или 'ДД.ММ.ГГ ЧЧ:ММ' и возвращает aware datetime в Asia/Tashkent.
    """
    s = " ".join((s or "").strip().split())
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{2}|\d{4})\s+(\d{1,2}):(\d{2})", s)
    if not m:
        raise ValueError("Неверный формат даты. Используйте ДД.ММ.ГГГГ ЧЧ:ММ")

    d, mth, y, h, mi = map(int, m.groups())
    if y < 100:  # '25' → 2025
        y += 2000

    try:
        naive = dt.datetime(y, mth, d, h, mi)
    except ValueError as e:
        raise ValueError(f"Неверная дата/время: {e}")

    return naive.replace(tzinfo=TZ)

def format_local_datetime(d: dt.datetime) -> str:
    """Возвращает строку в формате 'ДД.ММ.ГГГГ ЧЧ:ММ' в часовом поясе Asia/Tashkent."""
    return d.astimezone(TZ).strftime("%d.%m.%Y %H:%M")

# --- совместимость со старым именем ---
def format_date(date_str: str) -> dt.datetime:
    """DEPRECATED: оставлено для обратной совместимости."""
    return parse_local_datetime(date_str)
