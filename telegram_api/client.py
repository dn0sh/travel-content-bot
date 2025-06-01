# telegram_api/client.py
from typing import Optional
from aiogram.types import ContentType, FSInputFile, Message, User, InlineKeyboardMarkup, InlineKeyboardButton
from config.env import bot_global, conf
from config.logging_config import logger, async_log_exception


@async_log_exception
async def publish_post_to_group(chat_id: str, text: Optional[str] = None, image_url: Optional[str] = None) -> int:
    """Публикация поста в Telegram-группу и возврат message_id"""
    if not text and not image_url:
        raise ValueError("Должен быть указан хотя бы один из параметров: text или image_url")
    try:
        # Создаём кнопку с ссылкой на ваш профиль
        author_button = InlineKeyboardButton(
            text="📩 Написать автору",
            url=f"{conf.tg_bot.developer_url}"   # или tg://user?id={author_id}
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[author_button]])
        # Отправляем пост с кнопкой
        if image_url:
            photo = FSInputFile(image_url)
            result = await bot_global.send_photo(chat_id=chat_id, photo=photo, caption=text)
            # result = await bot_global.send_photo(chat_id=chat_id, photo=photo, caption=text, reply_markup=keyboard)
        else:
            result = await bot_global.send_message(chat_id=chat_id, text=text)
            # result = await bot_global.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
        return result.message_id  # Возвращаем ID сообщения
    except Exception as e:
        logger.error(f"Ошибка при публикации в группу {chat_id}: {e}", exc_info=True)
        raise
