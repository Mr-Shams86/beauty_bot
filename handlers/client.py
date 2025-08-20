# handlers/client.py
from __future__ import annotations

import logging
import datetime as dt
from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove

from config import ADMIN_ID
from utils.helpers import parse_local_datetime, format_local_datetime, TZ

# DB helpers
from database import (
    list_services,
    get_service_by_id,
    get_service_by_name,
    get_future_appointments_by_user,
    upsert_user,
    has_time_conflict,
)

# Сервисы (единая точка синхронизации)
from services.appointments import create_appointment_and_sync

from keyboards import confirmation_keyboard, client_menu

log = logging.getLogger(__name__)


class AppointmentForm(StatesGroup):
    name = State()
    service = State()   # тут храним service_id
    date = State()


async def start_menu(message: Message):
    """Приветственное меню клиента."""
    await message.answer(
        "👋 Добро пожаловать в салон красоты!\nВыберите действие из меню ниже:",
        reply_markup=client_menu,
    )


async def start_appointment(message: Message, state: FSMContext):
    """Запускает процесс записи, запрашивая имя."""
    await message.answer("Введите ваше имя:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AppointmentForm.name)


async def process_name(message: Message, state: FSMContext):
    """Сохраняет имя и предлагает услуги из справочника."""
    await state.update_data(name=(message.text or "").strip())

    services = await list_services()
    if not services:
        await message.answer("⚠️ Список услуг пока пуст. Попробуйте позже.")
        return

    lines = [f"{i+1}) {s.name} — {s.duration_min} мин."
             for i, s in enumerate(services)]
    await message.answer(
        "Выберите услугу, отправив номер или название:\n\n" + "\n".join(lines)
    )
    await state.set_state(AppointmentForm.service)


async def process_service(message: Message, state: FSMContext):
    """Принимает номер/название и сохраняет service_id."""
    raw = (message.text or "").strip()

    svc = None
    if raw.isdigit():
        idx = int(raw) - 1
        all_svcs = await list_services()
        if 0 <= idx < len(all_svcs):
            svc = all_svcs[idx]
    if not svc:
        svc = await get_service_by_name(raw, partial=True)
    if not svc:
        services = await list_services()
        lines = [f"{i+1}) {s.name} — {s.duration_min} мин."
                 for i, s in enumerate(services)]
        await message.answer(
            "❌ Не удалось распознать услугу.\n"
            "Отправьте номер из списка или точное название:\n\n" + "\n".join(lines)
        )
        return

    if not svc:
        await message.answer("❌ Не удалось распознать услугу. Отправьте номер из списка или точное название.")
        return

    await state.update_data(service_id=svc.id)
    await message.answer("Введите дату в формате <b>ДД.ММ.ГГГГ ЧЧ:ММ</b>:", parse_mode="HTML")
    await state.set_state(AppointmentForm.date)


async def process_date(message: Message, state: FSMContext):
    """Создаёт запись: БД → Calendar → Sheets, и шлёт подтверждение админу."""
    user_id = message.from_user.id
    data = await state.get_data()

    user_name = (data.get("name") or "").strip()
    service_id = data.get("service_id")
    date_raw = (message.text or "").strip()

    if not service_id:
        await message.answer("❌ Сначала выберите услугу.")
        await state.set_state(AppointmentForm.service)
        return

    # # 1) Парсинг и «не прошлое»./ Парсим локальную дату «ДД.ММ.ГГГГ ЧЧ:ММ» → aware datetime (Asia/Tashkent)
    try:
        appt_dt = parse_local_datetime(date_raw) # -> aware (Asia/Tashkent)
    except Exception:
        await message.answer("❌ Неверный формат. Используйте <b>ДД.ММ.ГГГГ ЧЧ:ММ</b>.", parse_mode="HTML")
        return

    if appt_dt < dt.datetime.now(tz=TZ):
        await message.answer("❌ Нельзя записаться на прошедшую дату.")
        return

    # 2) Подтянуть услугу и длительность
    svc = await get_service_by_id(service_id)
    if not svc:
        await message.answer("❌ Услуга не найдена. Попробуйте снова.")
        await state.set_state(AppointmentForm.service)
        return
    service_name = svc.name
    duration_min = svc.duration_min or 60  # по умолчанию 60 минут
    
    # 3) Конфликты
    if await has_time_conflict(appt_dt, duration_min):
        await message.answer("❌ Время занято. Выберите другое.")
        return
    
    # (опц.) обновим/создадим запись о пользователе
    fallback_name = (message.from_user.full_name or message.from_user.username or "").strip() or f"user_{user_id}"
    try:
        await upsert_user(telegram_id=user_id, name=user_name or fallback_name)
    except Exception as e:
        log.warning("upsert_user failed: %s", e)


    # 4) Создаём запись и синхронизируем (БД + Calendar + Sheets)
    try:
        appt_id = await create_appointment_and_sync(
            user_id=user_id,
            user_name=user_name,
            service_id=service_id,
            date=appt_dt,
        )
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return

    # 5) Шлём админу карточку с кнопками confirm/cancel
    await message.bot.send_message(
        ADMIN_ID,
        (
            "📅 <b>Новая запись</b>\n"
            f"🆔 {appt_id}\n"
            f"👤 {user_name}\n"
            f"💇 {service_name}\n"
            f"📍 Telegram: <code>{user_id}</code>\n"
            f"📅 {format_local_datetime(appt_dt)}"
        ),
        reply_markup=confirmation_keyboard(appt_id),
        parse_mode="HTML",
    )

    # Ответ клиенту
    await message.answer(
        "✅ Ваша заявка отправлена мастеру.\n"
        f"💇 Услуга: {service_name}\n"
        f"🕒 Когда: {format_local_datetime(appt_dt)}",
        reply_markup=client_menu,
    )
    await state.clear()


async def my_appointments(message: Message):
    """Показывает клиенту его будущие записи (из БД)."""
    user_id = message.from_user.id
    appts = await get_future_appointments_by_user(user_id)

    if not appts:
        await message.answer("📅 У вас пока нет будущих записей.")
        return

    lines = []
    for a in appts:
        svc_name = a.service.name if getattr(a, "service", None) else "Услуга"
        lines.append(f"• {svc_name} — {format_local_datetime(a.date)} — {a.status}")

    await message.answer("📋 <b>Ваши записи</b>:\n" + "\n".join(lines), parse_mode="HTML")


def register_client_handlers(dp: Dispatcher):
    """Регистрация клиентских хендлеров."""
    dp.message.register(start_menu, Command("start"))
    dp.message.register(my_appointments, Command("my"))
    
    dp.message.register(start_appointment, F.text == "✅ Записаться 📝")
    dp.message.register(my_appointments,  F.text == "✅ Мои записи 📅")

    dp.message.register(process_name,    AppointmentForm.name)
    dp.message.register(process_service, AppointmentForm.service)
    dp.message.register(process_date,    AppointmentForm.date)
