from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def confirmation_keyboard(appointment_id: int):
    """Создаёт клавиатуру с кнопками подтверждения и отмены записи."""
    if appointment_id is None:
        print("⚠️ Ошибка: передан пустой ID записи для кнопок подтверждения!")
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data=f"confirm_{appointment_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отменить", callback_data=f"cancel_{appointment_id}"
                ),
            ]
        ]
    )


# ✅ Клавиатура для клиентов
client_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Записаться 📝")],
        [KeyboardButton(text="✅ Мои записи 📅")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,  # ✅ Клавиатура исчезнет после нажатия
)


# 🛠 Основная клавиатура для администратора
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Список записей")],
        [
            KeyboardButton(text="🗑️ Удалить запись"),
            KeyboardButton(text="✏ Изменить запись"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,  # ✅ Клавиатура исчезнет после нажатия
)


# 📌 Инлайн-кнопки для управления записями (админская панель)
def admin_control_buttons(appointment_id: int):
    """Создаёт инлайн-клавиатуру с кнопками управления для администратора."""
    if appointment_id is None:
        print("⚠️ Ошибка: передан пустой ID записи для кнопок администратора!")
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data=f"confirm_{appointment_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отменить", callback_data=f"cancel_{appointment_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить запись", callback_data=f"delete_{appointment_id}"
                )
            ],
        ]
    )
