from aiogram import Router, F
from aiogram.types import Message
from src.services.llm_client import LLMClient
from src.бот.keyboards.main_menu import get_main_keyboard
import logging
import traceback

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text & ~F.text.startswith('/'))
async def handle_text(message: Message):
    """Обработчик текстовых сообщений"""
    user_text = message.text
    logger.info(f"Received text from user {message.from_user.id}: {user_text[:50]}...")
    
    # Показываем, что бот печатает
    await message.chat.do("typing")
    
    try:
        llm_client = LLMClient()
        # Анализируем только текст (без изображения)
        recipe = await llm_client.analyze_dish(text=user_text, image_bytes=None)
        
        # Формируем ответ
        response = format_recipe_response(recipe)
        await message.answer(response, reply_markup=get_main_keyboard(), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        logger.error(traceback.format_exc())
        await message.answer(
            "Извини, произошла ошибка при обработке твоего запроса. "
            "Пожалуйста, попробуй ещё раз или пришли фото продуктов.",
            reply_markup=get_main_keyboard()
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
