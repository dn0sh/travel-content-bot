# openai_api/client.py
import json
from openai import OpenAI, APIError, AuthenticationError, RateLimitError, OpenAIError
from config.env import conf
from config.logging_config import logger, async_log_exception

client = OpenAI(api_key=conf.openai.api_key)


@async_log_exception
async def generate_travel_themes(model: str = conf.openai.gpt_model, count: int = 4) -> dict:
    """
    Генерация тем для постов о путешествиях

    Args:
        model (str): Модель OpenAI (по умолчанию из конфига)
        count (int): Количество тем для генерации (по умолчанию 4)

    Returns:
        dict: {'themes': ["тема1", "тема2", ...]}
    """
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": f"""
Вы — эксперт по путешествиям. Сгенерируйте {count} уникальных тем для постов о путешествиях.

Требования:
- Каждая тема должна начинаться с эмодзи
- Формат темы: "эмодзи + краткое описание направления" (например: "❄️ Зимние чудеса Санкт-Петербурга")
- Обязательно включите хотя бы одну тему о путешествиях по России
- Темы должны охватывать разные типы путешествий (природа, культура, гастрономия, приключения)
- Избегайте повторяющихся форматов и локаций
- Не используйте шаблонные фразы из примеров

Важно:
- Ответ должен быть в строго определённом JSON-формате
- Ключ должен быть ТОЛЬКО "themes"
- Значение: список строк
- Ответ должен быть на языке пользователя (русский)
- Никаких лишних полей
- Не повторяйте темы

Пример формата ответа:
{{
    "themes": [
        "эмодзи Краткое описание темы 1",
        "эмодзи Краткое описание темы 2",
        ...
    ]

Пример ответа:
{{
    "themes": [
        "❄️ Зимние чудеса Санкт-Петербурга"
        "🌄 Удивительные пейзажи Новой Зеландии",
        "🏖️ Пляжи и культура Мальдив",
        "🏰 Исторические сокровища Италии",
        "🌴 Экзотическая природа и традиции Таиланда"
    ]
}}
"""},
                {"role": "user", "content": f"Сгенерируй {count} уникальных тем для постов о путешествиях, избегая повторов и стандартных примеров"}
                      ],
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        # Парсим JSON и извлекаем список тем
        response = completion.choices[0].message.content.strip()
        parsed = json.loads(response)
        # Проверка структуры
        if not isinstance(parsed, dict) or "themes" not in parsed:
            logger.warning("Ответ не содержит ключа 'themes'")
            raise ValueError("Некорректная структура JSON: отсутствует ключ 'themes'")
        themes = parsed["themes"]
        # Проверка количества тем
        if not isinstance(themes, list) or len(themes) != count:
            logger.warning(f"Количество тем не равно {count}")
            raise ValueError(f"Количество тем не равно {count}")
        logger.info(f"[OpenAI] Сгенерированы уникальные темы: {themes}")
        return {"themes": themes}
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"[OpenAI] Ошибка парсинга тем: {e}")
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
async def generate_text(prompt: str, model: str = conf.openai.gpt_model, max_tokens: int = 500, style: str = "casual") -> str:
    """
    Генерация текста через OpenAI API с возможностью выбора стиля

    Args:
        prompt (str): Текстовый запрос
        model (str): Модель OpenAI (по умолчанию из конфига)
        max_tokens (int): Максимальное количество токенов в ответе
        style (str): Стиль текста (casual, professional, humorous, poetic)
    Returns:
        str: Сгенерированный текст
    """
    try:
        # Определяем стиль текста
        style_instructions = {
            "casual": "Используйте дружелюбный и непринужденный стиль, как будто вы разговариваете с другом.",
            "professional": "Используйте формальный и профессиональный стиль, подходящий для делового контента.",
            "humorous": "Добавьте юмор и шутки в текст, сделайте его веселым и забавным.",
            "poetic": "Используйте поэтический стиль с метафорами и образами."
        }
        # Выбираем инструкции в зависимости от стиля
        selected_style = style_instructions.get(style.lower(), style_instructions["casual"])
        # Вызов OpenAI API
        completion = client.chat.completions.create(
            messages=[{'role': 'system', 'content': f'Вы SMM-эксперт. Генерируй тексты для Телеграмм канала на заданную тему. Длинна текста не должна превышать 900 символов. Можно использовать смайлики. {selected_style} Вопросы пользователю не задавай.'},
                      {'role': 'user', 'content': prompt}
            ],
            model=model,
            max_tokens=max_tokens,
            temperature=0.5
        )
        # Возврат сгенерированного текста
        return completion.choices[0].message.content.strip()
    except AuthenticationError as auth_error:
        raise Exception(f"Ошибка аутентификации OpenAI: {auth_error}")
    except APIError as api_error:
        raise Exception(f"Ошибка API OpenAI: {api_error}")
    except RateLimitError as rate_limit_error:
        raise Exception(f"Превышен лимит запросов к OpenAI: {rate_limit_error}")
    except OpenAIError as ex:
        raise Exception(f"Общая ошибка OpenAI: {ex}")
    except Exception as e:
        raise Exception(f"Ошибка генерации текста: {e}")


@async_log_exception
async def generate_image_prompt(post_text: str) -> str:
    """
    Генерация промпта для изображения на основе сгенерированного текста
    """
    try:
        completion = client.chat.completions.create(
            model=conf.openai.gpt_model,
            messages=[
                {'role': 'system', 'content': """Вы SMM-эксперт и визуальный дизайнер. 
                На основе текста поста сгенерируйте подробное описание изображения (10-20 слов), подходящее к тексту. 
                Включите в описание основные элементы, которые должны быть на изображении:
                - Местоположение/ландшафт
                - Люди/деятельность (если есть)
                - Цветовая палитра
                - Стиль изображения
                Не используйте смайлики. Сделайте описание максимально информативным для генерации изображения."""},
                {'role': 'user', 'content': f'Текст поста:\n{post_text}'}
            ],
            max_tokens=200,
            temperature=0.3
        )
        image_prompt = completion.choices[0].message.content.strip()
        logger.info(f"[OpenAI] Промпт для изображения: {image_prompt}")
        return image_prompt
    except Exception as e:
        logger.error(f"[OpenAI] Ошибка генерации промпта для изображения: {e}")
        raise


@async_log_exception
async def get_current_model() -> str:
    """Возвращает текущую модель OpenAI из конфигурации"""
    return conf.openai.gpt_model
