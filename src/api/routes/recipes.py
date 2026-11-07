from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from src.api.dependencies.auth import get_current_user
from typing import List, Optional
from pydantic import BaseModel
import json

router = APIRouter(prefix="/recipes", tags=["recipes"])

# Pydantic модели для запросов и ответов
class RecipeBase(BaseModel):
    name: str
    description: Optional[str] = None
    cooking_time: int  # в минутах
    difficulty: str
    servings: int
    cuisine: str

class RecipeCreate(RecipeBase):
    ingredients: List[dict]  # список ингредиентов с деталями
    steps: List[dict]      # список шагов
    nutrition: dict        # пищевая ценность
    chef_tip: Optional[str] = None
    serving_suggestion: Optional[str] = None
    image_prompt: Optional[str] = None

class RecipeResponse(RecipeBase):
    id: int
    user_id: int
    ingredients: List[dict]
    steps: List[dict]
    nutrition: dict
    chef_tip: Optional[str] = None
    serving_suggestion: Optional[str] = None
    image_prompt: Optional[str] = None
    created_at: str

    class Config:
        orm_mode = True

# Временное хранилище для MVP (в дальнейшем заменить на базу данных)
# В реальном приложении здесь будут вызовы к базе данных через SQLAlchemy
fake_recipes_db = {}

@router.post("/analyze-dish", response_model=RecipeResponse)
async def analyze_dish(
    text: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Анализировать блюдо по тексту и/или фото и вернуть рецепт.
    """
    # Для MVP возвращаем демо-рецепт
    recipe_id = len(fake_recipes_db) + 1
    recipe_data = {
        "id": recipe_id,
        "user_id": current_user["id"],
        "name": "Анализ блюда",
        "description": f"Рецепт на основе: {text[:50]}...",
        "cooking_time": 30,
        "difficulty": "Средняя",
        "servings": 2,
        "cuisine": "Домашняя",
        "ingredients": [
            {"name": "Ингредиент 1", "amount": "100 г", "calories": 100, "proteins": 5, "fats": 3, "carbs": 10},
            {"name": "Ингредиент 2", "amount": "50 г", "calories": 50, "proteins": 2, "fats": 1, "carbs": 5},
        ],
        "steps": [
            {"number": 1, "text": "Подготовьте ингредиенты", "duration_seconds": 300},
            {"number": 2, "text": "Приготовьте блюдо", "duration_seconds": 1200},
        ],
        "nutrition": {
            "calories": 300,
            "proteins": 15,
            "fats": 10,
            "carbs": 30
        },
        "chef_tip": "Совет шефа: добавьте специи по вкусу",
        "serving_suggestion": "Подавайте горчим",
        "image_prompt": "Delicious homemade dish",
        "created_at": "2026-11-07T00:00:00Z"
    }
    fake_recipes_db[recipe_id] = recipe_data
    return fake_recipes_db[recipe_id]

@router.post("/", response_model=RecipeResponse)
async def create_recipe(
    recipe: RecipeCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Сохранить новый рецепт для пользователя.
    """
    # В реальном приложении: сохранить в базу данных и вернуть сохраненный объект
    # Здесь используем временное хранилище
    recipe_id = len(fake_recipes_db) + 1
    recipe_data = recipe.dict()
    recipe_data.update({
        "id": recipe_id,
        "user_id": current_user["id"],
        "created_at": "2026-10-16T00:00:00Z"  # placeholder
    })
    fake_recipes_db[recipe_id] = recipe_data
    return recipe_data

@router.get("/", response_model=List[RecipeResponse])
async def get_user_recipes(
    current_user: dict = Depends(get_current_user),
    limit: int = 10,
    offset: int = 0
):
    """
    Получить список рецептов текущего пользователя с пагинацией.
    """
    # Фильтруем рецепты по user_id
    user_recipes = [
        recipe for recipe in fake_recipes_db.values()
        if recipe["user_id"] == current_user["id"]
    ]
    # Сортируем по дате создания (новые først)
    user_recipes.sort(key=lambda x: x["created_at"], reverse=True)
    return user_recipes[offset:offset + limit]

@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
    recipe_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Получить рецепт по ID, если он принадлежит текущему пользователю.
    """
    recipe = fake_recipes_db.get(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return recipe

@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Удалить рецепт по ID, если он принадлежит текущему пользователю.
    """
    recipe = fake_recipes_db.get(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    del fake_recipes_db[recipe_id]
    return None
