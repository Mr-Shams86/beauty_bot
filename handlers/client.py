from __future__ import annotations

import logging
import datetime as dt
from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery

from config import ADMIN_ID
from utils.helpers import parse_local_datetime, format_local_datetime, TZ

# DB helpers
from database import (
    list_services,
    get_service_by_id,
    get_service_by_name,
    get_future_appointments_by_user,
    get_appointment_by_id,
    upsert_user,
    has_time_conflict,
)

# Сервисы (единая точка синхронизации)
from services.appointments import (
    create_appointment_and_sync,
    reschedule_appointment_and_sync,
    delete_appointment_and_sync,
)

from keyboards import (
    confirmation_keyboard,
    client_menu,
    services_keyboard,          # инлайн-список услуг
    my_appointment_keyboard,    # инлайн для «Мои записи»
)

log = logging.getLogger(__name__)


# ===== FSM =====
class AppointmentForm(StatesGroup):
    name = State()
    service = State()   # храним service_id
    date = State()

class ClientReschedule(StatesGroup):
    waiting_for_new_date = State()


# ===== Меню / Старт =====
async def start_menu(message: Message):
    """Приветственное меню клиента."""
    await message.answer(
        "👋 Добро пожаловать в салон красоты!\nВыберите действие из меню ниже:",
        reply_markup=client_menu,
    )


# ===== Создание записи =====
async def start_appointment(message: Message, state: FSMContext):
    """Запускает процесс записи, запрашивая имя."""
    await message.answer("Введите ваше имя:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AppointmentForm.name)


async def process_name(message: Message, state: FSMContext):
    """Сохраняет имя и предлагает услуги из справочника (инлайн-кнопки + подсказка по номеру/названию)."""
    await state.update_data(name=(message.text or "").strip())

    services = await list_services()
    if not services:
        await message.answer("⚠️ Список услуг пока пуст. Попробуйте позже.")
        return

    lines = [f"{i+1}) {s.name} — {s.duration_min} мин." for i, s in enumerate(services)]
    await message.answer(
        "Выберите услугу кнопкой ниже или отправьте номер/название:\n\n" + "\n".join(lines),
        reply_markup=services_keyboard(services),
    )
    await state.set_state(AppointmentForm.service)


async def process_service(message: Message, state: FSMContext):
    """
    Принимает номер/название (если пользователь не нажал инлайн-кнопку)
    и сохраняет service_id.
    """
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
        lines = [f"{i+1}) {s.name} — {s.duration_min} мин." for i, s in enumerate(services)]
        await message.answer(
            "❌ Не удалось распознать услугу.\n"
            "Нажмите кнопку ниже или отправьте номер/точное название:\n\n" + "\n".join(lines),
            reply_markup=services_keyboard(services),
        )
        return

    await state.update_data(service_id=svc.id)
    await message.answer("Введите дату в формате <b>ДД.ММ.ГГГГ ЧЧ:ММ</b>:", parse_mode="HTML")
    await state.set_state(AppointmentForm.date)


async def select_service_callback(call: CallbackQuery, state: FSMContext):
    """
    Пользователь выбрал услугу инлайн-кнопкой `svc_{id}`.
    """
    try:
        service_id = int(call.data.split("_", 1)[1])
    except Exception:
        return await call.answer("Некорректная услуга", show_alert=True)

    svc = await get_service_by_id(service_id)
    if not svc:
        return await call.answer("Услуга не найдена", show_alert=True)

    await state.update_data(service_id=service_id)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer("Введите дату в формате <b>ДД.ММ.ГГГГ ЧЧ:ММ</b>:", parse_mode="HTML")
    await state.set_state(AppointmentForm.date)
    await call.answer()


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

    # 1) Парсим локальную дату и проверяем «не прошлое»
    try:
        appt_dt = parse_local_datetime(date_raw)  # -> aware (Asia/Tashkent)
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
    duration_min = svc.duration_min or 60

    # 3) Конфликты
    if await has_time_conflict(appt_dt, duration_min):
        await message.answer("❌ Время занято. Выберите другое.")
        return

    # (опц.) создать/обновить пользователя
    fallback_name = (message.from_user.full_name or message.from_user.username or "").strip() or f"user_{user_id}"
    try:
        await upsert_user(telegram_id=user_id, name=user_name or fallback_name)
    except Exception as e:
        log.warning("upsert_user failed: %s", e)

    # 4) Создание и синхронизация
    try:
        appt_id = await create_appointment_and_sync(
            user_id=user_id,
            user_name=user_name or fallback_name,
            service_id=service_id,
            date=appt_dt,
        )
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return

    # 5) Уведомление админу
    await message.bot.send_message(
        ADMIN_ID,
        (
            "📅 <b>Новая запись</b>\n"
            f"🆔 {appt_id}\n"
            f"👤 {user_name or fallback_name}\n"
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


# ===== Мои записи (просмотр + самообслуживание) =====
async def my_appointments(message: Message):
    """Показывает клиенту его будущие записи (из БД), с кнопками Перенести/Отменить."""
    user_id = message.from_user.id
    appts = await get_future_appointments_by_user(user_id)

    if not appts:
        await message.answer("📅 У вас пока нет будущих записей.")
        return

    await message.answer("📋 <b>Ваши записи</b>:", parse_mode="HTML")
    for a in appts:
        svc_name = a.service.name if getattr(a, "service", None) else "Услуга"
        text = f"• {svc_name}\n🕒 {format_local_datetime(a.date)}\n📌 Статус: {a.status}"
        await message.answer(text, reply_markup=my_appointment_keyboard(a.id))


# ===== Отмена клиентом =====
async def cli_cancel(call: CallbackQuery):
    try:
        appt_id = int(call.data.split("_", 2)[2])
    except Exception:
        return await call.answer("Некорректный ID", show_alert=True)

    appt = await get_appointment_by_id(appt_id)
    if not appt:
        return await call.answer("Запись не найдена", show_alert=True)

    if appt.user_id != call.from_user.id:
        return await call.answer("Эта запись не ваша.", show_alert=True)

    ok = await delete_appointment_and_sync(appt_id)
    if not ok:
        return await call.answer("Не удалось отменить. Попробуйте позже.", show_alert=True)

    await call.message.edit_text("❌ Запись отменена.")
    await call.answer("Готово")


# ===== Перенос клиентом (FSM) =====
async def cli_resched_start(call: CallbackQuery, state: FSMContext):
    try:
        appt_id = int(call.data.split("_", 2)[2])
    except Exception:
        return await call.answer("Некорректный ID", show_alert=True)

    appt = await get_appointment_by_id(appt_id)
    if not appt:
        return await call.answer("Запись не найдена", show_alert=True)

    if appt.user_id != call.from_user.id:
        return await call.answer("Эта запись не ваша.", show_alert=True)

    await state.update_data(resched_appt_id=appt_id)
    await call.message.answer("Введите новую дату в формате <b>ДД.ММ.ГГГГ ЧЧ:ММ</b>:", parse_mode="HTML")
    await state.set_state(ClientReschedule.waiting_for_new_date)
    await call.answer()


async def cli_resched_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    appt_id = data.get("resched_appt_id")
    if not appt_id:
        await message.answer("❌ Не найден ID записи.")
        return

    appt = await get_appointment_by_id(appt_id)
    if not appt:
        await message.answer("❌ Запись не найдена.")
        await state.clear()
        return

    try:
        new_dt = parse_local_datetime((message.text or "").strip())
    except Exception:
        await message.answer("❌ Неверный формат. Используйте <b>ДД.ММ.ГГГГ ЧЧ:ММ</b>.", parse_mode="HTML")
        return

    if new_dt < dt.datetime.now(tz=TZ):
        await message.answer("❌ Нельзя переносить в прошлое.")
        return

    # длительность берём из услуги/записи
    svc = await get_service_by_id(appt.service_id) if appt.service_id else None
    duration_min = getattr(svc, "duration_min", appt.duration_min or 60)

    if await has_time_conflict(new_dt, duration_min, exclude_id=appt.id):
        await message.answer("❌ Это время занято. Выберите другое.")
        return

    try:
        ok = await reschedule_appointment_and_sync(appt.id, new_dt)
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return

    if not ok:
        await message.answer("⚠️ Не удалось перенести запись.")
        return

    await message.answer(f"✅ Перенесли на {format_local_datetime(new_dt)}.")
    await state.clear()


# ===== Регистрация =====
def register_client_handlers(dp: Dispatcher):
    """Регистрация клиентских хендлеров."""
    # Команды
    dp.message.register(start_menu, Command("start"))
    dp.message.register(my_appointments, Command("my"))

    # Reply-кнопки
    dp.message.register(start_appointment, F.text == "✅ Записаться 📝")
    dp.message.register(my_appointments,  F.text == "✅ Мои записи 📅")

    # FSM создания
    dp.message.register(process_name,    AppointmentForm.name)
    dp.message.register(process_service, AppointmentForm.service)
    dp.message.register(process_date,    AppointmentForm.date)

    # Выбор услуги (инлайн)
    dp.callback_query.register(select_service_callback, F.data.startswith("svc_"))

    # Самообслуживание (инлайн)
    dp.callback_query.register(cli_cancel,        F.data.startswith("cli_cancel_"))
    dp.callback_query.register(cli_resched_start, F.data.startswith("cli_resched_"))
    dp.message.register(cli_resched_finish,       ClientReschedule.waiting_for_new_date)
