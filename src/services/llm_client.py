import json
import base64
import time
import re
import httpx
import logging
import os
from typing import Optional, Dict, Any
from src.config import config

# Системный промт повара с учетом интервью
СИСТЕМНЫЙ_ПРОМТ_ПОВАРА = """Ты — опытный шеф-повар и нутрициолог.
Верни JSON с рецептом. Все текстовые поля на русском.
image_prompt — на английском.
Формат: {
  "название_блюда", "описание", "время_готовки_минут", "сложность",
  "порций", "кухня",
  "ингредиенты": [{"название", "количество", "обязательный",
    "калории_на_100г", "белки_на_100г", "жиры_на_100г", "углеводы_на_100г",
    "калории_итого", "белки_итого_г", "жиры_итого_г", "углеводы_итого_г"}],
  "шаги": [{"номер", "текст", "длительность_секунд", "подсказка"}],
  "пищевая_ценность": {
    "калории_всего", "калории_на_порцию",
    "белки_всело_г", "жиры_всело_г", "углеводы_всело_г",
    "белки_на_порцию_г", "жиры_на_порцию_г", "углеводы_на_порцию_г",
    "процент_белков", "процент_жиров", "процент_углеводов",
    "теги": ["низкокалорийное", "высокобелковое", "пп"]
  },
  "совет_шефа", "рекомендация_подачи", "image_prompt"
}

КРИТИЧЕСКИ ВАЖНО ДЛЯ ТОЧНОСТИ КАЛОРИЙ:
- Для КАЖДОГО ингредиента указывай ТОЧНЫЙ ВЕС В ГРАММАХ в поле "количество" (например: "200 г", "150 г", "3 шт." -> "150 г").
- Поля "калории_на_100г", "белки_на_100г", "жиры_на_100г", "углеводы_на_100г" — это справочные значения на 100 грамм.
- Поля "калории_итого", "белки_итого_г", "жиры_итого_г", "углеводы_итого_г" — это РАСЧЕТНЫЕ значения для указанного веса.
- Python-код на бэкенде ПЕРЕСЧИТЫВАЕТ калории по ингредиентам. Если твои цифры не сойдутся — они будут пересчитаны.
- Указывай реалистичные веса: не "1 г" и не "10000 г".

Пользователь указал: [Порции], [Кухня], [Предпочтения]. Сгенерируй рецепт с учетом этих данных.
Обязательно указывай точный вес каждого ингредиента в граммах, чтобы Python-код мог точно рассчитать калории.

Предпочтения:
- "ПП" / "ЗОЖ" — низкокалорийное, высокобелковое, меньше жиров и сахаров.
- "Без мяса" — вегетарианское/веганское, замени мясо на бобовые/грибы/тофу.
- "Никаких" — классический рецепт без ограничений.

Кухня влияет на специи, соусы, методики приготовления."""

logger = logging.getLogger(__name__)

def clean_json_response(text: str) -> str:
    """Очищает ответ модели от markdown-разметки и лишнего текста."""
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    return text.strip()

def extract_json(text: str) -> dict:
    """Надежно извлекает JSON из текста с логированием сырого ответа."""
    cleaned = clean_json_response(text)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"[LLM] Direct JSON parse failed: {e}")
    
    md_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1))
        except json.JSONDecodeError:
            pass
    
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start != -1 and end != -1 and start < end:
        candidate = cleaned[start:end+1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    
    logger.error(f"[LLM] Failed to extract JSON. Raw response (first 1000 chars):\n{text[:1000]}")
    raise ValueError("Не удалось извлечь валидный JSON из ответа модели")


class LLMClient:
    def __init__(self):
        self.base_url = config.LLM_BASE_URL.rstrip("/")
        self.api_key = config.LLM_API_KEY
        self.model = config.LLM_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Отключаем прокси для localhost (Ollama)
        # trust_env=False отключает использование системных переменных HTTP_PROXY/HTTPS_PROXY
        self.timeout = httpx.Timeout(120.0, connect=10.0)
        self.max_retries = 1

    def _get_client(self) -> httpx.AsyncClient:
        """Создаёт клиент с использованием системных настроек прокси (VPN)."""
        return httpx.AsyncClient(
            timeout=self.timeout,
        )

    async def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        last_exception = None
        for attempt in range(self.max_retries + 1):
            start_time = time.time()
            try:
                url = f"{self.base_url}/chat/completions"
                print(f"[LLM DEBUG] POST URL: {url}")
                logger.info(f"[LLM DEBUG] POST URL: {url}")
                async with self._get_client() as client:
                    response = await client.post(
                        url,
                        headers=self.headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    result = response.json()
                    elapsed = time.time() - start_time
                    usage = result.get("usage", {})
                    logger.info(
                        f"[LLM] Model: {self.model}, "
                        f"Attempt: {attempt + 1}, "
                        f"Time: {elapsed:.2f}s, "
                        f"Tokens: {usage.get('total_tokens', 0)}"
                    )
                    return result
            except httpx.HTTPStatusError as e:
                last_exception = e
                elapsed = time.time() - start_time
                logger.error(f"[LLM] HTTP {e.response.status_code} on attempt {attempt + 1}: {e}, Time: {elapsed:.2f}s")
                if e.response.status_code == 503:
                    logger.error("[LLM] Ollama returned 503 (model unavailable). Check if model is loaded.")
                    raise
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                else:
                    raise
            except Exception as e:
                last_exception = e
                elapsed = time.time() - start_time
                logger.error(f"[LLM] Error on attempt {attempt + 1}: {e}, Time: {elapsed:.2f}s")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                else:
                    raise
        raise last_exception

    async def analyze_dish(self, text: str, image_bytes: Optional[bytes] = None,
                           servings: int = 2, cuisine: str = "Любая", 
                           preferences: str = "Никаких") -> Dict[str, Any]:
        # Формируем системный промт с учетом параметров интервью
        system_prompt = СИСТЕМНЫЙ_ПРОМТ_ПОВАРА.replace(
            "[Порции]", str(servings)
        ).replace(
            "[Кухня]", cuisine
        ).replace(
            "[Предпочтения]", preferences
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
        ]

        user_content = []
        if text:
            user_content.append({"type": "text", "text": text})

        if image_bytes:
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })

        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 8000,
            "response_format": {"type": "json_object"},
        }

        response = await self._make_request(payload)

        assistant_message = response["choices"][0]["message"]["content"]
        try:
            recipe_data = extract_json(assistant_message)
        except ValueError as e:
            logger.error(f"[LLM] Failed to parse JSON: {e}")
            logger.error(f"[LLM] Raw response (first 2000 chars):\n{assistant_message[:2000]}")
            raise

        return recipe_data
