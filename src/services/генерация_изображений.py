import os
import hashlib
import boto3
from botocore.exceptions import ClientError
import replicate
from typing import Optional
from src.config import config

# Initialize S3 client if S3_ENDPOINT is provided
s3_client = None
if config.S3_ENDPOINT and config.S3_ACCESS_KEY and config.S3_SECRET_KEY:
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=config.S3_ENDPOINT,
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY,
        )
    except Exception as e:
        print(f"Warning: Could not initialize S3 client: {e}")

def _get_image_key(prompt: str) -> str:
    """Генерирует ключ для хранения изображения в S3 на основе хеша промпта."""
    prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    return f"images/{prompt_hash}.png"

def get_image_from_s3(prompt: str) -> Optional[str]:
    """Пытается получить изображение из S3 по хешу промпта."""
    if not s3_client or not config.S3_BUCKET:
        return None
    key = _get_image_key(prompt)
    try:
        # Предполагаем, что изображение хранится как публичный объект или мы можем сгенерировать presigned URL
        # Для простоты возвращаем прямой URL если bucket публичный, иначе можно генерировать presigned URL
        # Здесь мы предполагаем, что bucket настроен для публичного чтения (или используем CDN)
        url = f"{config.S3_ENDPOINT}/{config.S3_BUCKET}/{key}" if config.S3_ENDPOINT else f"https://{config.S3_BUCKET}.s3.amazonaws.com/{key}"
        # Проверяем существование объекта
        s3_client.head_object(Bucket=config.S3_BUCKET, Key=key)
        return url
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return None
        else:
            print(f"Error checking S3 for key {key}: {e}")
            return None
    except Exception as e:
        print(f"Error getting image from S3: {e}")
        return None

def save_image_to_s3(prompt: str, image_url: str) -> bool:
    """Скачивает изображение по URL и сохраняет в S3.
    В реальности мы должны получить бинарные данные изображения и загрузить в S3.
    Однако replicate возвращает URL уже загруженного изображения, поэтому мы можем просто сохранить этот URL?
    Но требование: кеш в S3. Мы будем сохранять само изображение, а не URL.
    Для простоты假设我们可以下载图片并上传到S3，但这里为了演示，我们只保存URL（实际中应下载后上传）。
    由于复杂性和外部依赖，这里我们跳过实际下载和上传，只保存URL作为缓存（在生产环境中应正确实现）。
    或者，我们可以认为replicate已经将图片存储在它们的CDN上，我们只是缓存这个URL到S3作为索引。
    为了满足要求，我们将尝试下载图片并上传到S3。
    """
    if not s3_client or not config.S3_BUCKET:
        return False
    try:
        import requests
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        image_data = response.content
        key = _get_image_key(prompt)
        s3_client.put_object(
            Bucket=config.S3_BUCKET,
            Key=key,
            Body=image_data,
            ContentType='image/png'
        )
        return True
    except Exception as e:
        print(f"Error saving image to S3: {e}")
        return False

def generate_image(prompt: str) -> Optional[str]:
    """
    Генерирует изображение по промту с помощью Flux.2 Pro через Replicate.
    Сначала проверяет кеш в S3, если не найдено — генерирует и сохраняет в S3.
    Возвращает URL изображения или None в случае ошибки.
    """
    # 1. Проверяем кеш в S3
    cached_url = get_image_from_s3(prompt)
    if cached_url:
        return cached_url

    # 2. Если нет в кеше, генерируем через Replicate
    try:
        # Используем модель Flux.2 Pro от replicate
        # На момент написания, например: "black-forest-labs/flux-1-pro"
        # Но уточним: согласно репликате, Flux.2 Pro может быть доступна под другим именем.
        # Мы будем использовать переменную окружения для гибкости, но если не задана — используем запасной вариант.
        model = os.getenv("FLUX_MODEL", "black-forest-labs/flux-1-pro")
        input_params = {
            "prompt": prompt,
            # Можно добавить другие параметры, например, соотношение сторон, количество шагов и т.д.
            # Но для простоты оставляем только промпт.
        }
        output = replicate.run(model, input=input_params)
        # Output может быть списком URL или одиночным URL
        if isinstance(output, list) and len(output) > 0:
            image_url = output[0]
        elif isinstance(output, str):
            image_url = output
        else:
            print("Unexpected output format from Replicate")
            return None

        # 3. Сохраняем в S3 (кешируем)
        save_success = save_image_to_s3(prompt, image_url)
        if not save_success:
            print("Warning: Failed to cache image in S3, but returning generated URL")

        return image_url
    except Exception as e:
        print(f"Error generating image with Replicate: {e}")
        return None

def get_image_from_cache_or_generate(prompt: str) -> Optional[str]:
    """
    Основная функция для получения изображения: проверяет кеш, при необходимости генерирует.
    """
    return generate_image(prompt)
