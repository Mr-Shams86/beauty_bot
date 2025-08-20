# handlers/admin.py
from __future__ import annotations

import math

import logging

from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from utils.helpers import parse_local_datetime, format_local_datetime

from database import (
    get_appointments,
    get_appointment_by_id,
    add_appointment,
    update_appointment,
    update_appointment_status,
    update_appointment_event_id,
    delete_appointment,
)

from services.calendar import (
    add_event_to_calendar,
    update_event_in_calendar,
    delete_event_from_calendar,
    add_appointment_to_sheet,
    update_appointment_in_sheet,
    delete_appointment_from_sheet,
)

from keyboards import (
    admin_menu,                   # сам ReplyKeyboardMarkup
    ADMIN_MENU_LIST_LABEL,        # "📋 Список записей"
    ADMIN_MENU_DELETE_LABEL,      # "🗑️ Удалить запись"
    ADMIN_MENU_EDIT_LABEL,        # "✏ Изменить запись"
)

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

    appts = await get_appointments()
    if not appts:
        await message.answer("📋 Записей пока нет.")
        return

    lines = []
    for a in appts:
        svc_name = a.service.name if getattr(a, "service", None) else "Услуга"
        lines.append(
            f"🆔 {a.id} | 👤 {a.name or '-'} | 💇 {svc_name} | 📅 {format_local_datetime(a.date)}"
        )
    await message.answer("📋 <b>Список записей:</b>\n" + "\n".join(lines))


# ---- Удаление ----
async def delete_via_callback(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("Нет доступа", show_alert=True)
    try:
        appt_id = int(call.data.split("_", 1)[1])
    except Exception:
        return await call.answer("Некорректный ID", show_alert=True)

    appt = await get_appointment_by_id(appt_id)
    if not appt:
        return await call.answer("Запись не найдена", show_alert=True)

    svc_name = appt.service.name if getattr(appt, "service", None) else "Услуга"

    await delete_appointment_from_sheet(appt.name or "", svc_name, appt.date)
    if appt.event_id:
        await delete_event_from_calendar(appt.event_id)
    await delete_appointment(appt_id)

    await call.message.edit_text(f"❌ Запись ID {appt_id} удалена.")
    await call.bot.send_message(appt.user_id, "❌ Ваша запись отменена.")


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
    
    svc_name = appt.service.name if getattr(appt, "service", None) else "Услуга"

    # Google сначала (Sheets + Calendar), затем БД
    deleted_from_sheets = await delete_appointment_from_sheet(appt.name or "", svc_name, appt.date)
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

    ok = await update_appointment(appt_id, new_dt)
    if not ok:
        await message.answer("⚠️ Ошибка при обновлении базы данных!")
        return
    
    svc_name = appt.service.name if getattr(appt, "service", None) else "Услуга"

    if appt.event_id:
        duration_h = max(1, math.ceil((appt.duration_min or 60) / 60))
        await update_event_in_calendar(appt.event_id, appt.name or "Клиент", svc_name, new_dt, duration_hours=duration_h)

    await update_appointment_in_sheet(appt.name or "", svc_name, appt.date, new_dt)

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

    svc_name = appt.service.name if getattr(appt, "service", None) else "Услуга"

    if not appt.event_id:
        duration_h = max(1, math.ceil((appt.duration_min or 60) / 60))
        event_id = await add_event_to_calendar(appt.name or "Клиент", svc_name, appt.date, duration_hours=duration_h)
        if event_id:
            await update_appointment_event_id(appt_id, event_id)
            appt.event_id = event_id

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

    svc_name = appt.service.name if getattr(appt, "service", None) else "Услуга"

    await delete_appointment_from_sheet(appt.name or "", svc_name, appt.date)
    if appt.event_id:
        await delete_event_from_calendar(appt.event_id)

    ok = await delete_appointment(appt_id)
    if not ok:
        await call.message.answer("⚠️ Не удалось удалить запись из БД.")
        return

    await call.bot.send_message(
        appt.user_id,
        f"❌ Ваша запись на {svc_name} ({format_local_datetime(appt.date)}) отменена."
    )
    await call.message.edit_text("❌ Запись удалена и отменена везде.")



# ---- Регистрация ----
def register_admin_handlers(dp: Dispatcher):
    # СНАЧАЛА — обработчики со STATE!
    dp.message.register(process_delete, DeleteAppointment.waiting_for_id)
    dp.message.register(process_edit,   EditAppointment.waiting_for_id)
    dp.message.register(process_new_date, EditAppointment.waiting_for_new_date)

    # Потом — обычные команды/кнопки
    dp.message.register(admin_panel, Command("admin"))

    # фильтруем по тексту без эмодзи (на случай, если эмодзи изменятся)
    dp.message.register(
        show_appointments,
        F.text.contains(ADMIN_MENU_LIST_LABEL.replace("📋 ", ""))
    )
    dp.message.register(
        delete_appointment_handler,
        F.text.contains(ADMIN_MENU_DELETE_LABEL.replace("🗑️ ", ""))
    )
    dp.message.register(
        edit_appointment_handler,
        F.text.contains(ADMIN_MENU_EDIT_LABEL.replace("✏ ", ""))
    )

    # колбэки
    dp.callback_query.register(confirm_appointment, F.data.startswith("confirm_"))
    dp.callback_query.register(cancel_appointment,  F.data.startswith("cancel_"))
    dp.callback_query.register(delete_via_callback, F.data.startswith("delete_"))
