from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.services.llm_client import LLMClient
from src.бот.keyboards.main_menu import get_main_keyboard
from src.бот.keyboards.interview import (
    get_servings_keyboard,
    get_cuisine_keyboard,
    get_preferences_keyboard
)
from src.бот.states import RecipeInterview
import logging
import traceback

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text & ~F.text.startswith('/'), RecipeInterview.waiting_for_dish)
async def handle_dish_name(message: Message, state: FSMContext):
    """Первый шаг: пользователь вводит название блюда."""
    dish_name = message.text.strip()
    if not dish_name:
        await message.answer("Напиши название блюда, например: «Яичница» или «Паста карбонара».")
        return

    # Сохраняем название блюда в состоянии
    await state.update_data(dish_name=dish_name)
    await state.set_state(RecipeInterview.waiting_for_servings)

    await message.answer(
        f"Отлично, будем готовить: <b>{dish_name}</b>!\n\n"
        "🍽 <b>На сколько порций готовим?</b>",
        reply_markup=get_servings_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("servings:"), RecipeInterview.waiting_for_servings)
async def handle_servings(callback: CallbackQuery, state: FSMContext):
    """Второй шаг: выбор количества порций."""
    servings_map = {"servings:1": 1, "servings:2": 2, "servings:3": 4}
    servings = servings_map.get(callback.data, 2)
    
    await state.update_data(servings=servings)
    await state.set_state(RecipeInterview.waiting_for_cuisine)

    servings_text = "1 порцию" if servings == 1 else f"{servings} порции" if servings < 5 else "4+ порций"
    
    await callback.message.edit_text(
        f"✅ Порций: <b>{servings_text}</b>\n\n"
        "🌍 <b>Какая кухня?</b>",
        reply_markup=get_cuisine_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("cuisine:"), RecipeInterview.waiting_for_cuisine)
async def handle_cuisine(callback: CallbackQuery, state: FSMContext):
    """Третий шаг: выбор кухни."""
    cuisine = callback.data.split(":", 1)[1]
    await state.update_data(cuisine=cuisine)
    await state.set_state(RecipeInterview.waiting_for_preferences)

    await callback.message.edit_text(
        f"✅ Кухня: <b>{cuisine}</b>\n\n"
        "⚙️ <b>Есть ли предпочтения?</b>",
        reply_markup=get_preferences_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("preferences:"), RecipeInterview.waiting_for_preferences)
async def handle_preferences(callback: CallbackQuery, state: FSMContext):
    """Четвертый шаг: выбор предпочтений -> генерация рецепта."""
    preferences = callback.data.split(":", 1)[1]
    await state.update_data(preferences=preferences)
    
    # Получаем все собранные данные
    data = await state.get_data()
    dish_name = data.get("dish_name", "")
    servings = data.get("servings", 2)
    cuisine = data.get("cuisine", "Любая")
    preferences = data.get("preferences", "Никаких")

    await state.set_state(RecipeInterview.generating)
    
    # Показываем статус генерации
    await callback.message.edit_text(
        f"🍳 Готовлю рецепт...\n\n"
        f"🍽 Блюдо: <b>{dish_name}</b>\n"
        f"👥 Порций: <b>{servings}</b>\n"
        f"🌍 Кухня: <b>{cuisine}</b>\n"
        f"⚙️ Предпочтения: <b>{preferences}</b>",
        parse_mode="HTML"
    )
    await callback.answer()

    # Генерируем рецепт через LLM
    try:
        llm_client = LLMClient()
        recipe = await llm_client.analyze_dish(
            text=dish_name,
            image_bytes=None,
            servings=servings,
            cuisine=cuisine,
            preferences=preferences
        )

        # Формируем ответ
        response = format_recipe_response(recipe)
        await callback.message.answer(
            response,
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error generating recipe: {e}")
        logger.error(traceback.format_exc())
        await callback.message.answer(
            "Извини, произошла ошибка при генерации рецепта. Попробуй ещё раз.",
            reply_markup=get_main_keyboard()
        )
    finally:
        # Сбрасываем состояние после завершения
        await state.clear()

@router.message(F.text & ~F.text.startswith('/'))
async def handle_text(message: Message, state: FSMContext):
    """Обработчик текста вне FSM (или первый шаг)."""
    current_state = await state.get_state()
    
    if current_state == RecipeInterview.waiting_for_dish:
        # Если мы в процессе интервью, перенаправляем в обработчик блюда
        await handle_dish_name(message, state)
    else:
        # Начинаем новый цикл интервью
        await state.set_state(RecipeInterview.waiting_for_dish)
        await message.answer(
            "🍳 <b>Что будем готовить?</b>\n\n"
            "Напиши название блюда (например: «Яичница», «Борщ», «Паста карбонара») "
            "или опиши, что хочешь приготовить.",
            parse_mode="HTML"
        )

def safe_float(val, default=0.0):
    """Безопасно приводит значение к float."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def safe_int(val, default=0):
    """Безопасно приводит значение к int."""
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default

def format_recipe_response(recipe: dict) -> str:
    """Форматирует рецепт в читаемое сообщение"""
    name = recipe.get("название_блюда", "Без названия")
    description = recipe.get("описание", "")
    time = safe_int(recipe.get("время_готовки_минут", 0))
    difficulty = recipe.get("сложность", "?")
    servings = safe_int(recipe.get("порций", 1))
    cuisine = recipe.get("кухня", "?")

    # Ингредиенты - пересчитываем БЖУ в Python
    ingredients = recipe.get("ингредиенты", [])
    calc_proteins_total = sum(safe_float(ing.get("белки_итого_г", 0)) for ing in ingredients)
    calc_fats_total = sum(safe_float(ing.get("жиры_итого_г", 0)) for ing in ingredients)
    calc_carbs_total = sum(safe_float(ing.get("углеводы_итого_г", 0)) for ing in ingredients)
    calc_calories_total = calc_proteins_total * 4 + calc_fats_total * 9 + calc_carbs_total * 4

    if servings > 0:
        calc_proteins_per = calc_proteins_total / servings
        calc_fats_per = calc_fats_total / servings
        calc_carbs_per = calc_carbs_total / servings
        calc_calories_per = calc_calories_total / servings
    else:
        calc_proteins_per = calc_fats_per = calc_carbs_per = calc_calories_per = 0

    total_macro = calc_proteins_total + calc_fats_total + calc_carbs_total
    if total_macro > 0:
        calc_protein_pct = (calc_proteins_total / total_macro) * 100
        calc_fat_pct = (calc_fats_total / total_macro) * 100
        calc_carb_pct = (calc_carbs_total / total_macro) * 100
    else:
        calc_protein_pct = calc_fat_pct = calc_carb_pct = 0

    # Пищевая ценность (берём из модели, но пересчитанные используем для вывода)
    nutrition = recipe.get("пищевая_ценность", {})
    calories_total = calc_calories_total
    calories_per = calc_calories_per
    proteins_total = calc_proteins_total
    fats_total = calc_fats_total
    carbs_total = calc_carbs_total
    proteins_per = calc_proteins_per
    fats_per = calc_fats_per
    carbs_per = calc_carbs_per
    protein_pct = calc_protein_pct
    fat_pct = calc_fat_pct
    carb_pct = calc_carb_pct
    tags = nutrition.get("теги", [])

    # Формируем строку с тегами
    tags_str = " ".join([f"#{tag}" for tag in tags]) if tags else ""

    response = f"<b>{name}</b>\n"
    if description:
        response += f"{description}\n\n"
    response += (
        f"🕒 Время: {time} мин | 🔪 Сложность: {difficulty} | "
        f"🍽 Порций: {servings} | 🌍 Кухня: {cuisine}\n\n"
        f"<b>Калории и БЖУ:</b>\n"
        f"• Всего: {calories_total:.0f} ккал | {proteins_total:.1f}г белка | "
        f"{fats_total:.1f}г жиров | {carbs_total:.1f}г углеводов\n"
        f"• На порцию: {calories_per:.0f} ккал | {proteins_per:.1f}г | "
        f"{fats_per:.1f}г | {carbs_per:.1f}г\n"
        f"• Соотношение БЖУ: {protein_pct:.0f}% | {fat_pct:.0f}% | {carb_pct:.0f}%\n"
    )
    if tags_str:
        response += f"\n{tags_str}\n"

    # Ингредиенты
    ingredients = recipe.get("ингредиенты", [])
    if ingredients:
        response += "\n<b>Ингредиенты:</b>\n"
        for ing in ingredients:
            name_ing = ing.get("название", "")
            amount = ing.get("количество", "")
            mandatory = "✅" if ing.get("обязательный", False) else "⚪"
            calories_ing = safe_float(ing.get("калории_итого", 0))
            response += f"{mandatory} {name_ing}: {amount} (~{calories_ing:.0f} ккал)\n"

    # Шаги приготовления
    steps = recipe.get("шаги", [])
    if steps:
        response += "\n<b>Пошаговая инструкция:</b>\n"
        for step in steps:
            step_num = safe_int(step.get("номер", 0))
            step_text = step.get("текст", "")
            duration = safe_int(step.get("длительность_секунд", 0))
            hint = step.get("подсказка", "")
            time_str = f"{duration//60} мин {duration%60} сек" if duration >= 60 else f"{duration} сек"
            response += f"{step_num}. {step_text} ({time_str})"
            if hint:
                response += f" — {hint}"
            response += "\n"

    # Совет шефа
    chef_tip = recipe.get("совет_шефа", "")
    if chef_tip:
        response += f"\n<b>Совет шефа:</b> {chef_tip}\n"

    # Рекомендация подачи
    serving = recipe.get("рекомендация_подачи", "")
    if serving:
        response += f"\n<b>Рекомендация подачи:</b> {serving}\n"

    response += "\nСохрани рецепт или поделись им с друзьями! 👇"

    return response
