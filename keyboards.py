from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from typing import Sequence

# --- Общие инлайн-кнопки для записи (для админа) ---

def _confirm_cancel_row(appointment_id: int) -> list[InlineKeyboardButton]:
    """Ряд из двух кнопок: Подтвердить / Отменить (для админа)."""
    if appointment_id is None:
        raise ValueError("appointment_id не должен быть None")
    return [
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{appointment_id}"),
        InlineKeyboardButton(text="❌ Отменить",   callback_data=f"cancel_{appointment_id}"),
    ]

def confirmation_keyboard(appointment_id: int) -> InlineKeyboardMarkup:
    """Клавиатура только с подтверждением/отменой (для админа)."""
    return InlineKeyboardMarkup(inline_keyboard=[_confirm_cancel_row(appointment_id)])

def admin_control_buttons(appointment_id: int) -> InlineKeyboardMarkup:
    """Инлайн-кнопки управления для админа (под сообщением с записью)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _confirm_cancel_row(appointment_id),
            [InlineKeyboardButton(text="🗑 Удалить запись", callback_data=f"delete_{appointment_id}")],
        ]
    )

# --- Инлайн: выбор услуги (для клиента) ---

def services_keyboard(services: Sequence, cols: int = 2) -> InlineKeyboardMarkup:
    """Список услуг с кнопками, расположенными по cols в ряд."""
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for i, svc in enumerate(services, 1):
        row.append(InlineKeyboardButton(text=svc.name, callback_data=f"svc_{svc.id}"))
        if i % cols == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

# --- Инлайн: управление своей записью (для клиента) ---

def my_appointment_keyboard(appointment_id: int) -> InlineKeyboardMarkup:
    """Инлайн-кнопки для клиента: перенос / отмена записи."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🔁 Перенести", callback_data=f"cli_resched_{appointment_id}"),
            InlineKeyboardButton(text="❌ Отменить",  callback_data=f"cli_cancel_{appointment_id}"),
        ]]
    )

# --- Reply-меню ---

client_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Записаться 📝")],
        [KeyboardButton(text="✅ Мои записи 📅")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,   # скрывается после первого нажатия
)

ADMIN_MENU_LIST_LABEL   = "📋 Список записей"
ADMIN_MENU_DELETE_LABEL = "🗑 Удалить запись"
ADMIN_MENU_EDIT_LABEL   = "✏ Изменить запись"

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=ADMIN_MENU_LIST_LABEL)],
        [KeyboardButton(text=ADMIN_MENU_DELETE_LABEL), KeyboardButton(text=ADMIN_MENU_EDIT_LABEL)],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)
