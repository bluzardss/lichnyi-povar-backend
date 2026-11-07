from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from src.api.dependencies.auth import get_current_user
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter(prefix="/images", tags=["images"])

class ImageGenerateRequest(BaseModel):
    prompt: str
    recipe_id: Optional[int] = None  # если изображение для конкретного рецепта

class ImageResponse(BaseModel):
    id: str
    url: str
    prompt: str
    recipe_id: Optional[int] = None
    created_at: str

    class Config:
        orm_mode = True

# Временное хранилище для изображений
fake_images_db = {}

@router.post("/generate", response_model=ImageResponse)
async def generate_image(request: ImageGenerateRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    Сгенерировать изображение блюда по промпту.
    В реальном приложении здесь будет вызов к сервису генерации изображений (Flux.2 Pro через Replicate/OpenRouter).
    """
    # Генерируем уникальный ID для изображения
    image_id = str(uuid.uuid4())
    # В реальном приложении здесь будет вызов к сервису генерации и загрузка в S3
    # Для MVP возвращаем заглушку
    image_url = f"https://via.placeholder.com/600x400.png?text={request.prompt.replace(' ', '+')}"
    
    image_data = {
        "id": image_id,
        "url": image_url,
        "prompt": request.prompt,
        "recipe_id": request.recipe_id,
        "created_at": "2026-10-16T00:00:00Z"
    }
    fake_images_db[image_id] = image_data
    return image_data

@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Получить информацию о сгенерированном изображении по ID.
    """
    image = fake_images_db.get(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    # В реальном приложении здесь будет проверка, что изображение принадлежит пользователю
    # Но для MVP пропустим проверку ownership (предполагаем, что пользователь может видеть свои изображения)
    return image

@router.delete("/{image_id}", status_code=204)
async def delete_image(
    image_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Удалить изображение по ID.
    """
    image = fake_images_db.get(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    # В реальном приложении здесь будет проверка ownership и удаление из S3
    del fake_images_db[image_id]
    return None
