from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

# --- Общие инлайн-кнопки для записи ---

def _confirm_cancel_row(appointment_id: int) -> list[InlineKeyboardButton]:
    """Ряд из двух кнопок: Подтвердить / Отменить."""
    if appointment_id is None:
        raise ValueError("appointment_id не должен быть None")
    return [
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{appointment_id}"),
        InlineKeyboardButton(text="❌ Отменить",   callback_data=f"cancel_{appointment_id}"),
    ]


def confirmation_keyboard(appointment_id: int) -> InlineKeyboardMarkup:
    """Клавиатура только с подтверждением/отменой (для клиента)."""
    return InlineKeyboardMarkup(inline_keyboard=[_confirm_cancel_row(appointment_id)])


def admin_control_buttons(appointment_id: int) -> InlineKeyboardMarkup:
    """Инлайн-кнопки управления для админа (под сообщением с записью)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _confirm_cancel_row(appointment_id),
            [InlineKeyboardButton(text="🗑 Удалить запись", callback_data=f"delete_{appointment_id}")],
        ]
    )


# --- Новые: выбор услуги + управление своими записями ---

def services_keyboard(services: list) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком услуг (каждая кнопка = service_id).
    services: список объектов с .id и .name
    """
    rows = [[InlineKeyboardButton(text=svc.name, callback_data=f"svc_{svc.id}")]
            for svc in services]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_appointment_controls(appointment_id: int) -> InlineKeyboardMarkup:
    """Инлайн для управления записью клиентом (перенос/отмена)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Перенести", callback_data=f"resched_{appointment_id}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data=f"usercancel_{appointment_id}"),
            ]
        ]
    )


# --- Reply-меню ---

# Клиентское меню (исчезает после нажатия — удобно для UX)
client_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Записаться 📝")],
        [KeyboardButton(text="✅ Мои записи 📅")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,   # скрывается после первого нажатия
)

# Админ-меню (оставляем постоянным, чтобы не пропадало)
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
