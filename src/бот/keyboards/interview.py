from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def get_servings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора количества порций."""
    builder = InlineKeyboardBuilder()
    builder.button(text="1 порция", callback_data="servings:1")
    builder.button(text="2 порции", callback_data="servings:2")
    builder.button(text="3+ порции", callback_data="servings:3")
    builder.adjust(3)  # 3 buttons in a row
    return builder.as_markup()

def get_cuisine_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора кухни."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русская", callback_data="cuisine:Русская")
    builder.button(text="🇮🇹 Итальянская", callback_data="cuisine:Итальянская")
    builder.button(text="🌏 Азиатская", callback_data="cuisine:Азиатская")
    builder.button(text="🍽 Любая", callback_data="cuisine:Любая")
    builder.adjust(2)  # 2 buttons per row
    return builder.as_markup()

def get_preferences_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора предпочтений."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🥗 ПП / ЗОЖ", callback_data="preferences:ПП")
    builder.button(text="🌱 Без мяса", callback_data="preferences:Без мяса")
    builder.button(text="❌ Никаких", callback_data="preferences:Никаких")
    builder.adjust(2, 1)  # 2 buttons first row, 1 second row
    return builder.as_markup()