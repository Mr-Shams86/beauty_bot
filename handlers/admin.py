# handlers/admin.py (async версия)
from __future__ import annotations
import logging

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from utils.helpers import parse_local_datetime, format_local_datetime

# БД (async)
from database import (
    get_appointments,
    get_appointment_by_id,
    add_appointment,                 # на будущее
    update_appointment,
    update_appointment_status,
    update_appointment_event_id,
    delete_appointment,
)

# Google (async)
from services.calendar import (
    add_event_to_calendar,
    update_event_in_calendar,
    delete_event_from_calendar,
    add_appointment_to_sheet,
    update_appointment_in_sheet,
    delete_appointment_from_sheet,
)

from keyboards import admin_menu

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


# ---- FSM ----
class DeleteAppointment(StatesGroup):
    waiting_for_id = State()


class EditAppointment(StatesGroup):
    waiting_for_id = State()
    waiting_for_new_date = State()


# ---- Админ-панель ----
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа!")
        return
    await message.answer("🔹 Панель администратора:\nВыберите действие:", reply_markup=admin_menu)


# ---- Просмотр всех записей ----
async def show_appointments(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа!")
        return

    appts = await get_appointments()  # list[Appointment]
    if not appts:
        await message.answer("📋 Записей пока нет.")
        return

    lines = []
    for a in appts:
        lines.append(f"🆔 {a.id} | 👤 {a.name} | 💇 {a.service} | 📅 {format_local_datetime(a.date)}")
    await message.answer("📋 <b>Список записей:</b>\n" + "\n".join(lines))


# ---- Удаление ----
async def delete_appointment_handler(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа!")
        return
    await message.answer("Введите <b>ID</b> записи, которую хотите удалить:")
    await state.set_state(DeleteAppointment.waiting_for_id)


async def process_delete(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    try:
        appt_id = int(text)
    except ValueError:
        await message.answer("❌ Ошибка! ID записи должен быть числом.")
        await state.clear()
        return

    appt = await get_appointment_by_id(appt_id)
    if not appt:
        await message.answer("❌ Запись не найдена!")
        await state.clear()
        return

    # Google сначала (Sheets + Calendar), затем БД
    deleted_from_sheets = await delete_appointment_from_sheet(appt.name, appt.service, appt.date)
    if appt.event_id:
        await delete_event_from_calendar(appt.event_id)

    ok = await delete_appointment(appt_id)
    if not ok:
        await message.answer("⚠️ Ошибка при удалении записи из базы данных!")
        return

    await message.answer(
        f"✅ Запись <b>ID {appt_id}</b> удалена.\n"
        f"{'📄 Удалена из Google Sheets' if deleted_from_sheets else '⚠️ В Google Sheets запись не найдена'}"
    )
    await state.clear()


# ---- Редактирование ----
async def edit_appointment_handler(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа!")
        return
    await message.answer("Введите <b>ID</b> записи, которую хотите изменить:")
    await state.set_state(EditAppointment.waiting_for_id)


async def process_edit(message: Message, state: FSMContext):
    appt_id_txt = (message.text or "").strip()
    try:
        appt_id = int(appt_id_txt)
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
        await state.clear()
        return

    appt = await get_appointment_by_id(appt_id)
    if not appt:
        await message.answer("❌ Запись не найдена!")
        await state.clear()
        return

    await state.update_data(appointment_id=appt_id)
    await message.answer("Введите новую дату в формате <b>ДД.ММ.ГГГГ ЧЧ:ММ</b>:")
    await state.set_state(EditAppointment.waiting_for_new_date)


async def process_new_date(message: Message, state: FSMContext):
    data = await state.get_data()
    appt_id: int | None = data.get("appointment_id")

    if not appt_id:
        await message.answer("❌ Ошибка: не найдено ID записи!")
        return

    appt = await get_appointment_by_id(appt_id)
    if not appt:
        await message.answer("❌ Запись не найдена!")
        await state.clear()
        return

    try:
        new_dt = parse_local_datetime((message.text or "").strip())
    except Exception:
        await message.answer("❌ Неверный формат. Используйте <b>ДД.ММ.ГГГГ ЧЧ:ММ</b>.")
        return

    # Обновляем в БД
    ok = await update_appointment(appt_id, new_dt)
    if not ok:
        await message.answer("⚠️ Ошибка при обновлении базы данных!")
        return

    # Google Calendar
    if appt.event_id:
        await update_event_in_calendar(appt.event_id, appt.name, appt.service, new_dt)
    # Google Sheets
    await update_appointment_in_sheet(appt.name, appt.service, appt.date, new_dt)

    await message.answer(f"✅ Запись <b>ID {appt_id}</b> перенесена на {format_local_datetime(new_dt)}.")
    await state.clear()


# ---- Подтверждение ----
async def confirm_appointment(call: CallbackQuery):
    appt_id_txt = call.data.split("_", 1)[1]
    try:
        appt_id = int(appt_id_txt)
    except ValueError:
        await call.message.answer("❌ Некорректный ID.")
        return

    appt = await get_appointment_by_id(appt_id)
    if not appt:
        await call.message.answer("❌ Запись не найдена.")
        return

    ok = await update_appointment_status(appt_id, "Подтверждено")
    if not ok:
        await call.message.answer("⚠️ Не удалось обновить статус.")
        return

    # Если в календаре ещё нет — создаём событие и привязываем event_id
    if not appt.event_id:
        event_id = await add_event_to_calendar(appt.name, appt.service, appt.date)
        if event_id:
            await update_appointment_event_id(appt_id, event_id)
            appt.event_id = event_id

    # уведомление пользователю
    await call.bot.send_message(
        appt.user_id,
        f"✅ Ваша запись подтверждена!\n📅 {format_local_datetime(appt.date)}"
    )

    await call.message.edit_text(
        f"✅ Запись ID {appt_id} подтверждена.\n"
        f"📅 {format_local_datetime(appt.date)}\n"
        f"📌 Calendar ID: {appt.event_id or '—'}"
    )


# ---- Отмена ----
async def cancel_appointment(call: CallbackQuery):
    appt_id_txt = call.data.split("_", 1)[1]
    try:
        appt_id = int(appt_id_txt)
    except ValueError:
        await call.message.answer("❌ Некорректный ID.")
        return

    appt = await get_appointment_by_id(appt_id)
    if not appt:
        await call.message.answer("❌ Запись не найдена.")
        return

    # Google
    await delete_appointment_from_sheet(appt.name, appt.service, appt.date)
    if appt.event_id:
        await delete_event_from_calendar(appt.event_id)

    # БД
    ok = await delete_appointment(appt_id)
    if not ok:
        await call.message.answer("⚠️ Не удалось удалить запись из БД.")
        return

    # уведомление пользователю
    await call.bot.send_message(
        appt.user_id,
        f"❌ Ваша запись на {appt.service} ({format_local_datetime(appt.date)}) отменена."
    )

    await call.message.edit_text("❌ Запись удалена и отменена везде.")


# ---- Регистрация ----
def register_admin_handlers(dp: Dispatcher):
    dp.message.register(admin_panel, Command("admin"))
    dp.message.register(show_appointments, lambda m: m.text == "📋 Список записей")

    dp.message.register(delete_appointment_handler, lambda m: m.text == "🗑 Удалить запись")
    dp.message.register(process_delete, DeleteAppointment.waiting_for_id)

    dp.message.register(edit_appointment_handler, lambda m: m.text == "✏ Изменить запись")
    dp.message.register(process_edit, EditAppointment.waiting_for_id)
    dp.message.register(process_new_date, EditAppointment.waiting_for_new_date)

    dp.callback_query.register(confirm_appointment, lambda c: c.data.startswith("confirm_"))
    dp.callback_query.register(cancel_appointment,  lambda c: c.data.startswith("cancel_"))
