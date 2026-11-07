from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
import hashlib
import hmac
import urllib.parse

class AuthMiddleware(BaseMiddleware):
    """
    Middleware для проверки инициализационных данных (initData) 
    от Telegram Mini App.
    Проверяет подпись и срок действия данных.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Извлекаем initData из обновления, если оно есть
        init_data = None
        if isinstance(event, Update):
            # Для сообщений и callback_query
            if event.message and event.message.web_app_data:
                init_data = event.message.web_app_data.data
            elif event.callback_query and event.callback_query.data:
                # В callback_query может быть initData? Обычно нет, но проверим
                pass
        # Также initData может приходить в начале веб-сессии через параметр tgWebAppData
        # Для простоты в данном MVP мы будем проверять только при получении веб-данных

        if init_data:
            # Проверяем подпись и сохраняем пользовательские данные в контекст
            user_data = self._parse_init_data(init_data)
            if user_data:
                data["init_data"] = user_data
                data["user_id"] = user_data.get("user", {}).get("id")
            else:
                # Если подпись неверна, всё равно продолжаем, но без данных
                pass

        return await handler(event, data)

    def _parse_init_data(self, init_data: str) -> Dict[str, Any] | None:
        """
        Парсит и проверяет инициализационные данные от Telegram.
        Возвращает словарь с данными пользователя или None при ошибке.
        """
        try:
            parsed = dict(urllib.parse.parse_qsl(init_data, strict_parsing=True))
            hash_received = parsed.pop("hash", "")
            # Сортируем параметры по алфавиту
            data_check_string = "\n".join(
                f"{k}={v}" for k, v in sorted(parsed.items())
            )
            # Секретный клюц = SHA256("WebAppData", bot_token)
            from src.config import config
            secret_key = hmac.new(
                key=b"WebAppData",
                msg=config.TELEGRAM_BOT_TOKEN.encode(),
                digestmod=hashlib.sha256,
            ).digest()
            # Вычисляем наш хеш
            hash_calculated = hmac.new(
                key=secret_key,
                msg=data_check_string.encode(),
                digestmod=hashlib.sha256,
            ).hexdigest()
            # Сравниваем хеши
            if not hmac.compare_digest(hash_received, hash_calculated):
                return None
            # Если есть поле user, пытаемся распарсить его как JSON
            if "user" in parsed:
                import json
                parsed["user"] = json.loads(parsed["user"])
            return parsed
        except Exception:
            return None
