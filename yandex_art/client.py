# yandex_art/client.py
import base64
import os
import requests
import time
from datetime import datetime
from typing import Optional
from config.env import conf
from config.logging_config import logger, async_log_exception


@async_log_exception
async def generate_image(prompt: str, seed: int = 42, aspect_ratio: str = "1:1", style: str = "photorealistic") -> Optional[str]:
    """
    Генерация изображения через Yandex.Art API с дополнительными параметрами

    Args:
        prompt (str): Описание изображения
        seed (int): Зерно генерации (для воспроизводимости)
        aspect_ratio (str): Соотношение сторон (например, "16:9")
        style (str): Стиль изображения. Возможные значения:
                     - "photorealistic": реалистичное фото
                     - "vivid": насыщенные цвета и высокая детализация
                     - "natural": реалистичный стиль с естественными цветами
                     - "artistic": художественный стиль
                     - "minimalistic": минималистичный стиль
    Returns:
        Optional[str]: Путь к сохраненному изображению или None в случае ошибки
    """
    # Базовый URL Yandex.Art API
    yandex_art_model_uri = f"art://{conf.yandex.folder_id}/{conf.yandex.art_model}"
    # Определяем стили изображений
    image_styles = {
        "photorealistic": "реалистичное фото, высокая детализация, профессиональная фотография",
        "vivid": "насыщенные цвета, высокий уровень детализации",
        "natural": "реалистичный стиль, естественные цвета",
        "artistic": "художественный стиль с акцентами кисти",
        "minimalistic": "минималистичный стиль с простыми формами"
    }
    # Выбираем стиль
    selected_style = image_styles.get(style.lower(), image_styles["photorealistic"])
    full_prompt = f"{prompt}, {selected_style}"
    # Парсинг пропорций
    try:
        width_ratio, height_ratio = map(int, aspect_ratio.split(":"))
    except ValueError:
        raise ValueError("aspect_ratio должен быть в формате 'ширина:высота', например '16:9'")
    headers = {
        "Authorization": f"Bearer {conf.yandex.art_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "modelUri": yandex_art_model_uri,
        "generationOptions": {
            "seed": seed,
            "aspectRatio": {
                "widthRatio": width_ratio,
                "heightRatio": height_ratio
            }
        },
        "messages": [{
            "weight": 1,
            "text": full_prompt
        }]
    }
    try:
        # Шаг 1: Отправка асинхронного запроса
        response = requests.post(conf.yandex.art_api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        # Шаг 2: Получение ID операции
        operation_id = response.json()["id"]
        logger.debug(f"[Yandex.Art] Операция создана: {operation_id}")

        # Шаг 3: Ожидание завершения генерации
        while True:
            status_response = requests.get(
                f"https://llm.api.cloud.yandex.net/operations/{operation_id}",
                headers=headers
            )
            status_response.raise_for_status()
            result = status_response.json()
            if result.get("done"):
                # Шаг 4: Декодирование и сохранение изображения
                image_data = base64.b64decode(result["response"]["image"])
                # Создаем папку media, если её нет
                os.makedirs("media", exist_ok=True)
                # Генерируем уникальное имя файла с датой и временем
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                image_path = f"media/generated_image_{timestamp}.jpg"
                with open(image_path, "wb") as f:
                    f.write(image_data)
                logger.debug(f"[Yandex.Art] Изображение сохранено: {image_path}")
                return image_path
            logger.debug("[Yandex.Art] Ожидание завершения генерации...")
            time.sleep(1)
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if "response" in locals() and response.status_code == 401:
            error_msg += " | Проверьте IAM-токен и роль сервисного аккаунта (ai.imageGeneration.user)"
        elif "response" in locals() and response.status_code == 400:
            error_msg += " | Некорректные параметры запроса (проверьте пропорции и зерно)"
        logger.exception(f"[Ошибка Yandex.Art] {error_msg}")
        return None
