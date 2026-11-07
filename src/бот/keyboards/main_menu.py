from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import WebAppInfo
from src.config import config

def get_main_keyboard():
    """Создаёт главную клавиатуру бота с кнопкой открытия Mini App."""
    builder = ReplyKeyboardBuilder()
    # Кнопка открытия WebApp
    if config.TELEGRAM_WEBAPP_URL:
        builder.button(
            text="📱 Открыть приложение",
            web_app=WebAppInfo(url=config.TELEGRAM_WEBAPP_URL)
        )
    else:
        # Если URL не настроен, просто показываем информационную кнопку
        builder.button(text="📱 Приложение скоро будет доступно")
    builder.adjust(1)  # одна кнопка в строке
    return builder.as_markup(resize_keyboard=True)
