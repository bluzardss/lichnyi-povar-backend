from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from src.бот.keyboards.main_menu import get_main_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_name = message.from_user.full_name
    await message.answer(
        f"Привет, {user_name}! 👨‍🍳\n"
        "Я твой личный повар. Отправь мне фото продуктов или опиши, что хочешь приготовить, "
        "а я подберу рецепт с расчётом калорий и БЖУ.",
        reply_markup=get_main_keyboard()
    )

@router.message(Command(commands=["help"]))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    await message.answer(
        "Как пользоваться ботом:\n"
        "1. Пришли фото продуктов или готового блюда\n"
        "2. Или напиши текстом, что хочешь приготовить (например: ' хочу приготовить омлет из 2 яиц и помидоров')\n"
        "3. Бот проанализирует твой ввод и вернёт рецепт с:\n"
        "   - Названием и описанием блюда\n"
        "   - Временем готовки и сложностью\n"
        "   - Ингредиентами с калорийностью и БЖУ\n"
        "   - Пошаговой инструкцией с таймерами\n"
        "   - Советом шефа и рекомендацией подачи\n"
        "   - Промптом для генерации изображения блюда\n"
        "4. Сохраняй рецепты в историю и делись ими с друзьями!\n\n"
        "Доступные команды:\n"
        "/start - начать работу с ботом\n"
        "/help - показать эту справку"
    )
