# handlers/client.py (async версия)
from __future__ import annotations
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from utils.helpers import parse_local_datetime, format_local_datetime

# БД
from sqlalchemy import select
from database import (
    Appointment,
    add_appointment,                    # не используется здесь напрямую, но пусть будет
    get_appointments,
    get_appointment_by_id,
)

# Сервисы (единая точка синхронизации)
from services.appointments import (
    create_appointment_and_sync,        # БД + Google Calendar + Google Sheets
)

from keyboards import confirmation_keyboard, client_menu


class AppointmentForm(StatesGroup):
    name = State()
    service = State()
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
    """Сохраняет имя и запрашивает услугу."""
    await state.update_data(name=message.text.strip())
    await message.answer("Выберите услугу:\n1️⃣ Стрижка\n2️⃣ Укладка\n3️⃣ Окрашивание")
    await state.set_state(AppointmentForm.service)


async def process_service(message: Message, state: FSMContext):
    """Сохраняет услугу и запрашивает дату."""
    await state.update_data(service=message.text.strip())
    await message.answer("Введите дату в формате ДД.ММ.ГГГГ ЧЧ:ММ:")
    await state.set_state(AppointmentForm.date)


async def process_date(message: Message, state: FSMContext):
    """Создаёт запись: БД → Calendar → Sheets, и шлёт подтверждение админу."""
    SERVICE_NAMES = {"1": "Стрижка ✂️", "2": "Укладка 💇‍♀️", "3": "Окрашивание 🎨"}

    user_id = message.from_user.id
    user_data = await state.get_data()
    name_raw = (user_data.get("name") or "").strip()
    service_raw = (user_data.get("service") or "").strip()
    date_raw = (message.text or "").strip()

    service_name = SERVICE_NAMES.get(service_raw, service_raw or "Неизвестная услуга ❓")

    # Парсим локальную дату «ДД.ММ.ГГГГ ЧЧ:ММ» → aware datetime (Asia/Tashkent)
    try:
        appt_dt = parse_local_datetime(date_raw)
    except Exception:
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ ЧЧ:ММ")
        return

    # Создаём запись и синхронизируем (БД + Calendar + Sheets)
    appt_id = await create_appointment_and_sync(
        user_id=user_id,
        name=name_raw,
        service=service_name,
        date=appt_dt,
    )

    # Шлём админу карточку с кнопками confirm/cancel
    await message.bot.send_message(
        ADMIN_ID,
        (
            "📅 <b>Новая запись</b>\n"
            f"🆔 {appt_id}\n"
            f"👤 {name_raw}\n"
            f"💇 {service_name}\n"
            f"📍 Telegram: <code>{user_id}</code>\n"
            f"📅 {format_local_datetime(appt_dt)}"
        ),
        reply_markup=confirmation_keyboard(appt_id),
    )

    # Ответ клиенту
    await message.answer(
        "✅ Ваша заявка отправлена мастеру.\n"
        f"💇 Вы выбрали: {service_name}\n"
        f"📅 Дата: {format_local_datetime(appt_dt)}",
        reply_markup=client_menu,
    )
    await state.clear()


async def my_appointments(message: Message):
    """Показывает клиенту его записи (из БД)."""
    user_id = message.from_user.id
    appts = [a for a in await get_appointments() if a.user_id == user_id]

    if not appts:
        await message.answer("📅 У вас пока нет записей.")
        return

    lines = [
        f"📌 {a.name} — {a.service} — {format_local_datetime(a.date)}"
        for a in appts
    ]
    await message.answer("📋 Ваши записи:\n" + "\n".join(lines))


def register_client_handlers(dp: Dispatcher):
    """Регистрация клиентских хендлеров."""
    dp.message.register(start_menu, Command("start"))
    dp.message.register(start_appointment, lambda m: m.text == "✅ Записаться 📝")
    dp.message.register(my_appointments,  lambda m: m.text == "✅ Мои записи 📅")
    dp.message.register(process_name,     AppointmentForm.name)
    dp.message.register(process_service,  AppointmentForm.service)
    dp.message.register(process_date,     AppointmentForm.date)
