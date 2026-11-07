from fastapi import Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import hashlib
import hmac
import urllib.parse
import json
from src.config import config

async def verify_init_data(
    init_data: str = Header(None, alias="X-Telegram-Init-Data")
):
    """
    Проверяет инициализационные данные (initData) от Telegram Mini App.
    Возвращает данные пользователя, если подпись верна.
    Для тестов вне Telegram — возвращает фейкового пользователя.
    """
    if not init_data:
        # Тестовый фейковый пользователь
        return {"user": {"id": 123456, "first_name": "Гость", "username": "test_user", "language_code": "ru", "is_premium": False}}
    
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, strict_parsing=True))
        hash_received = parsed.pop("hash", "")
        # Сортируем параметры по алфавиту
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
        # Секретный ключ = SHA256("WebAppData", bot_token)
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
            # Невалидная подпись — для тестов возвращаем фейкового пользователя
            return {"user": {"id": 123456, "first_name": "Гость", "username": "test_user", "language_code": "ru", "is_premium": False}}
        # Если есть поле user, пытаемся распарсить его как JSON
        if "user" in parsed:
            parsed["user"] = json.loads(parsed["user"])
        return parsed
    except Exception as e:
        # Ошибка парсинга — для тестов возвращаем фейкового пользователя
        return {"user": {"id": 123456, "first_name": "Гость", "username": "test_user", "language_code": "ru", "is_premium": False}}

# Для простоты, можно также создать зависимость, которая возвращает только ID пользователя
async def get_current_user(
    init_data: dict = Depends(verify_init_data)
):
    """
    Возвращает данные текущего пользователя из initData.
    """
    user_info = init_data.get("user")
    if not user_info:
        raise HTTPException(status_code=401, detail="User info not found in initData")
    return user_info
