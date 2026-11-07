# Инициализация пакета маршрутов
from .recipes import router as рецепты
from .user import router as пользователь
from .images import router as изображения

__all__ = ['рецепты', 'пользователь', 'изображения']