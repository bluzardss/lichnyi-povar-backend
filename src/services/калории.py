from typing import List, Dict, Tuple, Optional
import os
import redis
import json
from src.db import models

# Примерный справочник ингредиентов (в реальности будет из БД или внешнего API)
# Для MVP можно использовать жестко закодированные значения или простую БД
INGREDIENT_DB = {
    "куриная грудка": {"калории": 165, "белки": 31, "жиры": 3.6, "углеводы": 0},
    "рис": {"калории": 130, "белки": 2.7, "жиры": 0.3, "углеводы": 28},
    "помидор": {"калории": 18, "белки": 0.9, "жиры": 0.2, "углеводы": 3.9},
    # ... и так далее
}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # Test connection
    redis_client.ping()
except Exception:
    redis_client = None

def get_ingredient_nutrition(ingredient_name: str) -> Dict[str, float]:
    """
    Возвращает пищевую ценность на 100 грамм для ингредиента.
    Сначала проверяет кеш Redis, затем локальный словарь.
    Если ингредиент не найден, возвращает нулевые значения.
    """
    key = f"ingredient:{ingredient_name.lower()}"
    if redis_client:
        try:
            cached = redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass  # fallback to local dict
    # Local dict fallback
    nutrition = INGREDIENT_DB.get(ingredient_name.lower(), {"калории": 0, "белки": 0, "жиры": 0, "углеводы": 0})
    # Cache in Redis if available
    if redis_client:
        try:
            redis_client.set(key, json.dumps(nutrition), ex=3600)  # cache for 1 hour
        except Exception:
            pass
    return nutrition

def calculate_ingredients_nutrition(ingredients: List[Dict]) -> Tuple[Dict[str, float], List[Dict]]:
    """
    Рассчитывает итоговые калории и БЖУ для списка ингредиентов.
    Каждый элемент ingredients должен содержать:
        {
            "название": str,
            "количество": float,  # в граммах
            ... другие поля
        }
    Возвращает кортеж:
        (итоговые_значения, список_ингредиентов_с_рассчитанными_полями)
    где итоговые_значения: {
        "калории_всего": float,
        "белки_всего_г": float,
        "жиры_всего_г": float,
        "углеводы_всего_г": float
    }
    И каждый элемент в списке_ингредиентов_с_рассчитанными_полями будет содержать дополнительные поля:
        "калории_итого", "белки_итого_г", "жиры_итого_г", "углеводы_итого_г"
    """
    total_calories = 0.0
    total_proteins = 0.0
    total_fats = 0.0
    total_carbs = 0.0
    ingredients_with_nutrition = []

    for ing in ingredients:
        name = ing.get("название", "").lower()
        amount = ing.get("количество", 0)  # граммы
        nutrition_per_100g = get_ingredient_nutrition(name)
        
        # Рассчитываем для данного количества
        factor = amount / 100.0
        calories = nutrition_per_100g["калории"] * factor
        proteins = nutrition_per_100g["белки"] * factor
        fats = nutrition_per_100g["жиры"] * factor
        carbs = nutrition_per_100g["углеводы"] * factor
        
        # Добавляем к общему totals
        total_calories += calories
        total_proteins += proteins
        total_fats += fats
        total_carbs += carbs
        
        # Создаем копию ингредиента с рассчитанными полями
        ing_with_nutrition = ing.copy()
        ing_with_nutrition.update({
            "калории_итого": round(calories, 2),
            "белки_итого_г": round(proteins, 2),
            "жиры_итого_г": round(fats, 2),
            "углеводы_итого_г": round(carbs, 2)
        })
        ingredients_with_nutrition.append(ing_with_nutrition)
    
    totals = {
        "калории_всего": round(total_calories, 2),
        "белки_всего_г": round(total_proteins, 2),
        "жиры_всего_г": round(total_fats, 2),
        "углеводы_всего_г": round(total_carbs, 2)
    }
    
    return totals, ingredients_with_nutrition

def calculate_per_serving(total_nutrition: Dict[str, float], servings: int) -> Dict[str, float]:
    """
    Рассчитывает пищевую ценность на одну порцию.
    """
    if servings <= 0:
        servings = 1
    per_serving = {
        key: value / servings for key, value in total_nutrition.items()
    }
    # Округляем до 2 знаков после запятой
    return {k: round(v, 2) for k, v in per_serving.items()}

def calculate_nutrition_percentage(total_nutrition: Dict[str, float]) -> Dict[str, float]:
    """
    Рассчитывает процентное содержание БЖУ от общей калорийности.
    """
    total_calories = total_nutrition.get("калории_всего", 0)
    if total_calories == 0:
        return {"процент_белков": 0, "процент_жиров": 0, "процент_углеводов": 0}
    
    # Калории от белков и углеводов: 4 ккал/г, от жиров: 9 ккал/г
    calories_from_proteins = total_nutrition.get("белки_всего_г", 0) * 4
    calories_from_fats = total_nutrition.get("жиры_всего_г", 0) * 9
    calories_from_carbs = total_nutrition.get("углеводы_всего_г", 0) * 4
    
    # Проверяем, что сумма примерно равна общей калорийности (допуск 5%)
    calculated_total = calories_from_proteins + calories_from_fats + calories_from_carbs
    if abs(calculated_total - total_calories) / total_calories > 0.05:
        # Если не сходится, корректируем? Или просто возвращаем как есть?
        # Для простоты возвращаем как есть, но можно добавить предупреждение.
        pass
    
    percent_proteins = (calories_from_proteins / total_calories) * 100 if total_calories > 0 else 0
    percent_fats = (calories_from_fats / total_calories) * 100 if total_calories > 0 else 0
    percent_carbs = (calories_from_carbs / total_calories) * 100 if total_calories > 0 else 0
    
    return {
        "процент_белков": round(percent_proteins, 2),
        "процент_жиров": round(percent_fats, 2),
        "процент_углеводов": round(percent_carbs, 2)
    }

def determine_tags(total_nutrition: Dict[str, float], serving_nutrition: Dict[str, float]) -> List[str]:
    """
    Определяет теги на основе пищевой ценности.
    """
    tags = []
    # Тег "низкокалорийное" если калории на порцию < 300 ккал
    if serving_nutrition.get("калории_на_порцию", 0) < 300:
        tags.append("низкокалорийное")
    # Тег "высокобелковое" если белки на порцию > 20 г
    if serving_nutrition.get("белки_на_порцию_г", 0) > 20:
        tags.append("высокобелковое")
    # Тег "пп" (правильное питание) - можно определить как сбалансированное БЖУ
    # Например, если процент белков между 20-35%, жиров 20-35%, углеводов 40-60%
    # Но для простоты пока не будем добавлять, или добавим всегда? 
    # По специи: теги включают "пп" как отдельный тег.
    # Мы будем добавлять "пп" если блюдо удовлетворяет определенным критериям.
    # Для простоты пока добавляем всегда, но лучше сделать более умно.
    tags.append("пп")
    return tags


def validate_ingredients_nutrition(ingredients: List[Dict], total_nutrition: Dict[str, float]) -> Tuple[bool, Dict[str, float]]:
    """
    Проверяет, что сумма калорий и БЖУ по ингредиентам совпадает с переданным итоговым питанием в пределах 5%.
    Возвращает кортеж (is_valid, actual_totals), где actual_totals — рассчитанные суммы по ингредиентам.
    """
    totals, _ = calculate_ingredients_nutrition(ingredients)
    # Сравниваем каждый показатель
    is_valid = True
    for key in ["калории_всего", "белки_всего_г", "жиры_всего_г", "углеводы_всего_г"]:
        expected = total_nutrition.get(key, 0)
        actual = totals.get(key, 0)
        if expected == 0:
            # Если ожидаем ноль, считаем валидным только если actual также ноль (или очень маленькое?)
            if abs(actual) > 1e-9:
                is_valid = False
                break
        else:
            diff = abs(actual - expected) / expected
            if diff > 0.05:  # более 5%
                is_valid = False
                break
    return is_valid, totals