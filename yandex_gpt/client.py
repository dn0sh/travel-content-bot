# yandex_gpt/client.py
import json
import aiohttp
from config.env import conf
from config.logging_config import logger, async_log_exception

# Глобальный экземпляр клиента
_client = None

class YandexGPTClient:
    def __init__(self):
        self.api_key = conf.yandex.gpt_api_key
        self.api_url = conf.yandex.gpt_api_url
        self.folder_id = conf.yandex.folder_id
        self.gpt_model = conf.yandex.gpt_model
        self.model_uri = f"gpt://{self.folder_id}/{self.gpt_model}"

    def get_model(self) -> str:
        """
        Возвращает текущую используемую модель YandexGPT
        
        Returns:
            str: Имя модели (например, "yandexgpt/latest")
        """
        return self.gpt_model

    async def _make_request(self, prompt_data: dict):
        """Базовый метод для выполнения запросов к YandexGPT"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        self.api_url,
                        headers=headers,
                        json=prompt_data,
                        timeout=30
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"YandexGPT API error: {response.status} - {error_text}")
                        return None
                    return await response.json()
        except Exception as e:
            logger.error(f"Ошибка при запросе к YandexGPT: {e}", exc_info=True)
            return None


@async_log_exception
async def generate_travel_themes(model: str = "yandexgpt/latest", count: int = 4) -> dict:
    """
    Генерация уникальных тем для постов о путешествиях

    Args:
        model (str): Модель YandexGPT
        count (int): Количество тем для генерации

    Returns:
        dict: {'themes': ["тема1", "тема2", ...]}
    """
    client = YandexGPTClient()
    system_prompt = f"""Ты эксперт по путешествиям. Строго следуй инструкциям.

    ЗАДАЧА:
    Сгенерируй {count} уникальных тем для постов о путешествиях в строго заданном JSON-формате.

    ТРЕБОВАНИЯ:
    1. Каждая тема начинается с эмодзи.
    2. Формат темы: "эмодзи + краткое описание направления" (например: "❄️ Зимние чудеса Санкт-Петербурга").
    3. Обязательно включи хотя бы одну тему о путешествиях по России.
    4. Темы должны охватывать разные типы путешествий (природа, культура, гастрономия, приключения).
    5. Избегайте повторяющихся форматов и локаций
    6. Не используйте шаблонные фразы из примеров
    5. Используй только русский язык.
    6. НЕ ДОБАВЛЯЙ ПОЯСНЕНИЙ, ТОЛЬКО JSON.
    7. СТРОГО СЛЕДУЙ СТРУКТУРЕ: {{ "themes": ["тема1", "тема2", ...] }}.

    ПРИМЕР ОТВЕТА:
    {{
        "themes": [
            "❄️ Зимние чудеса Санкт-Петербурга",
            "🌄 Удивительные пейзажи Новой Зеландии",
            "🏖️ Пляжи и культура Мальдив",
            "🏰 Исторические сокровища Италии",
            "🌴 Экзотическая природа и традиции Таиланда"
        ]
    }}
    """
    request_data = {
        "modelUri": client.model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 2000
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": f"Сгенерируй {count} уникальных тем для постов о путешествиях, избегая повторов и стандартных примеров"}
        ]
    }
    response = await client._make_request(request_data)
    if not response or "result" not in response:
        logger.warning("822.98 Не удалось получить ответ от YandexGPT")
        # Возвращаем fallback темы
        return {
            "themes": [
                "❄️ Зимние чудеса Санкт-Петербурга",
                "🏰 Исторические сокровища Италии",
                "🌌 Ночные приключения под звёздным небом Сахары",
                "🍜 Гастрономическое путешествие по уличным рынкам Бангкока"
            ]
        }
    # Парсим ответ
    try:
        content = response["result"]["alternatives"][0]["message"]["text"]
        # Убираем лишние символы и пробуем спарсить JSON
        clean_content = content.strip().replace("```json", "").replace("```", "")
        parsed = json.loads(clean_content)
        if not isinstance(parsed, dict) or "themes" not in parsed:
            raise ValueError("Некорректная структура JSON: отсутствует ключ 'themes'")
        themes = parsed["themes"]
        if not isinstance(themes, list) or len(themes) != count:
            raise ValueError(f"Количество тем не равно {count}")
        logger.info(f"822.80 [YandexGPT] Сгенерированы темы: {themes}")
        return {"themes": themes}
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"822.99 [YandexGPT] Ошибка парсинга тем: {e}")
        # Возвращаем fallback темы
        return {
            "themes": [
                "🌿 Экотуризм на Алтае",
                "🌄 Удивительные пейзажи Новой Зеландии",
                "🏖️ Пляжи и культура Мальдив",
                "🏔️ Горные приключения в Альпах",
                "🌴 Экзотическая природа и традиции Таиланда",
                "🌿 Эко-путешествия по скрытым уголкам Амазонки",
                "🏔️ Экстремальные треккинги в горах Патагонии",
                "🎨 Арт-туры по скрытым галереям Парижа"
            ]
        }


@async_log_exception
async def generate_text(prompt: str, model: str = "yandexgpt/latest", max_tokens: int = 500, style: str = "casual") -> str:
    """
    Генерация текста через YandexGPT API с возможностью выбора стиля

    Args:
        prompt (str): Текстовый запрос
        model (str): Модель YandexGPT
        max_tokens (int): Максимальное количество токенов в ответе
        style (str): Стиль текста (casual, professional, humorous, poetic)

    Returns:
        str: Сгенерированный текст
    """
    client = YandexGPTClient()
    # Определяем стиль текста
    style_instructions = {
        "casual": "Используйте дружелюбный и непринужденный стиль, как будто вы разговариваете с другом.",
        "professional": "Используйте формальный и профессиональный стиль, подходящий для делового контента.",
        "humorous": "Добавьте юмор и шутки в текст, сделайте его веселым и забавным.",
        "poetic": "Используйте поэтический стиль с метафорами и образами."
    }
    # Выбираем инструкции в зависимости от стиля
    selected_style = style_instructions.get(style.lower(), style_instructions["casual"])
    system_prompt = f"""Вы SMM-эксперт. Генерируй тексты для Телеграмм канала на заданную тему. 
    Длина текста должна быть примерно 900 символов. Используй эмодзи.

    {selected_style}
    Вопросы пользователю не задавайте."""
    request_data = {
        "modelUri": client.model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": 0.5,
            "maxTokens": max_tokens
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": prompt}
        ]
    }
    response = await client._make_request(request_data)
    if not response or "result" not in response:
        logger.error("[YandexGPT] Не удалось получить ответ от API")
        raise Exception("Не удалось получить ответ от YandexGPT")
    try:
        content = response["result"]["alternatives"][0]["message"]["text"]
        return content.strip()
    except Exception as e:
        logger.error(f"[YandexGPT] Ошибка извлечения текста: {e}")
        raise Exception(f"Ошибка извлечения текста из ответа YandexGPT: {e}")


@async_log_exception
async def generate_image_prompt(post_text: str) -> str:
    """
    Генерация промпта для изображения на основе сгенерированного текста

    Args:
        post_text (str): Текст поста

    Returns:
        str: Промпт для генерации изображения
    """
    client = YandexGPTClient()
    system_prompt = """Вы SMM-эксперт и визуальный дизайнер. 
    На основе текста поста сгенерируйте подробное описание изображения (20-25 слов), подходящее к тексту. 
    Включите в описание основные элементы, которые должны быть на изображении:
    - Местоположение/ландшафт
    - Люди/деятельность (если есть)
    - Цветовая палитра
    - Стиль изображения
    Не используйте смайлики. Сделайте описание максимально информативным для генерации изображения."""
    request_data = {
        "modelUri": client.model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": 0.3,
            "maxTokens": 300
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": f"Текст поста:\n{post_text}"}
        ]
    }
    response = await client._make_request(request_data)
    if not response or "result" not in response:
        logger.error("[YandexGPT] Не удалось получить ответ от API")
        raise Exception("Не удалось получить ответ от YandexGPT")
    try:
        content = response["result"]["alternatives"][0]["message"]["text"]
        image_prompt = content.strip()
        logger.info(f"[YandexGPT] Промпт для изображения: {image_prompt}")
        return image_prompt
    except Exception as e:
        logger.error(f"[YandexGPT] Ошибка извлечения промпта: {e}")
        raise Exception(f"Ошибка извлечения промпта из ответа YandexGPT: {e}")


@async_log_exception
async def get_current_model() -> str:
    """Возвращает текущую модель YandexGPT из глобального клиента"""
    global _client
    if _client is None:
        _client = YandexGPTClient()
    return _client.get_model()
