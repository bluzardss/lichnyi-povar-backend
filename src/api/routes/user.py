from fastapi import APIRouter, Depends, HTTPException
from src.api.dependencies.auth import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/user", tags=["user"])

class UserProfile(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None

    class Config:
        orm_mode = True

@router.get("/me", response_model=UserProfile)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Получить информацию о текущем пользователе.
    """
    # В реальном приложении здесь будет запрос к базе данных для получения профиля
    # Пока возвращаем данные из initData
    return UserProfile(
        id=current_user["id"],
        first_name=current_user.get("first_name"),
        last_name=current_user.get("last_name"),
        username=current_user.get("username"),
        language_code=current_user.get("language_code"),
        is_premium=current_user.get("is_premium", False)
    )

# Можно добавить эндпоинты для обновления настроек, диет и т.д.
