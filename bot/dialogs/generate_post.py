# bot/dialogs/generate_post.py
import re
from aiogram import F
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Back, Button, Calendar, Column, Next, Radio, Row, SwitchTo, Start
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.media import DynamicMedia
from dataclasses import dataclass
from datetime import datetime, time as dt_time
from sqlalchemy.future import select
from bot.dialogs import states
from bot.dialogs.common import MAIN_MENU_MAIN_BUTTON
from bot.themes import set_global_themes, get_global_themes
from config.config import generate_travel_themes, generate_text, generate_image_prompt, get_current_model
from config.env import conf, datetime_local
from config.logging_config import logger, async_log_exception
from database.db import save_post_to_db
from database.models import GenerationType, Post, AsyncSessionLocal
from yandex_art.client import generate_image
from scheduler.jobs import schedule_post_job
from telegram_api.client import publish_post_to_group


TRAVEL_THEMES_KEY = 'key_themes'
TRAVEL_THEMES_ID = 'themes_select'


@dataclass
class TravelThemesGroup:
    id: int
    name: str


@async_log_exception
async def on_text_prompt(message: Message, widget, dialog_manager: DialogManager, text: str):
    """
    Получение текстового промпта и генерация текста
    """
    # Показываем статус генерации
    status_msg = await message.answer("<b>⏳ Генерация текста...</b>")
    try:
        post_text = await generate_text(text)
        # Сохраняем в диалог
        dialog_manager.dialog_data['post_text'] = post_text  # Сгенерированный текст
        dialog_manager.dialog_data['text_prompt'] = text
        dialog_manager.dialog_data['model_text'] = await get_current_model()
        dialog_manager.dialog_data['generated_at_text'] = datetime_local()
        dialog_manager.dialog_data['status_text'] = GenerationType.SUCCESS
        # Сохраняем пост и сохраняем его ID
        post = await save_post_to_db(dialog_manager.dialog_data)
        dialog_manager.dialog_data['post_id'] = post.id  # Сохраняем ID поста
        await status_msg.delete()
        # Переход к следующему шагу
        await dialog_manager.switch_to(states.PostStates.waiting_for_text_prompt)
    except Exception as e:
        dialog_manager.dialog_data['status_text'] = GenerationType.ERROR
        dialog_manager.dialog_data['error_message'] = str(e)
        await status_msg.edit_text(f'<b>❌ Ошибка при генерации текста:</b> {e}')


@async_log_exception
async def on_text_prompt_callback(callback: CallbackQuery, button: Button, dialog_manager: DialogManager, selected_button):
    """
    Обработка нажатия на тему — запуск генерации текста
    """
    try:
        theme_index = int(selected_button.replace("theme_", ""))  # Например, "theme_0" → 0
        # Получаем темы из глобального хранилища
        themes = get_global_themes()
        selected_theme = None
        # Достаём тему из списка themes['themes'] по индексу
        try:
            selected_theme = themes['themes'][theme_index]
        except IndexError:
            logger.debug(f'❌ Ошибка: тема с индексом {theme_index} не найдена')
            await callback.message.answer(f"❌ Тема с индексом {theme_index} не найдена")
        except KeyError:
            logger.debug('❌ Ошибка: ключ "themes" отсутствует в данных')
            await callback.message.answer("❌ Темы не загружены")
        dialog_manager.dialog_data["selected_theme"] = selected_theme
        dialog_manager.dialog_data["text_prompt"] = selected_theme
        # Переход к генерации текста
        await on_text_prompt(message=callback.message, widget=None, dialog_manager=dialog_manager, text=selected_theme)
        # Переход к следующему шагу
        await dialog_manager.switch_to(states.PostStates.waiting_for_text_prompt)
    except IndexError as e:
        logger.error(f"Некорректный индекс темы: {e}")
        await callback.message.answer(f"❌ Тема не найдена: {e}")
    except Exception as e:
        logger.error(f"Ошибка при обработке темы: {e}")
        await callback.message.answer(f"❌ Ошибка: {e}")


@async_log_exception
async def on_generate_image_prompt(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Генерация промпта для изображения на основе текста"""
    data = dialog_manager.dialog_data
    post_text = data.get("post_text")
    if not post_text:
        await callback.message.answer("<b>❌ Сначала сгенерируйте текст</b>")
        return
    # Показываем статус генерации
    status_msg = await callback.message.answer("<b>⏳ Генерация промпта для изображения...</b>")
    dialog_manager.dialog_data["skip_image"] = False
    try:
        # Генерация промпта для изображения
        image_prompt = await generate_image_prompt(post_text)
        data["image_prompt"] = image_prompt  # Сохраняем в диалог
        data["auto_image_prompt"] = True     # Флаг автогенерации
        await status_msg.delete()
        # Переход к следующему шагу
        await dialog_manager.switch_to(states.PostStates.preview_auto_prompt)
    except Exception as e:
        await status_msg.edit_text(f"<b>❌ Ошибка при генерации промпта:</b> {e}")


@async_log_exception
async def on_skip_image(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    data = dialog_manager.dialog_data
    dialog_manager.dialog_data["skip_image"] = True


@async_log_exception
async def auto_prompt_getter(dialog_manager: DialogManager, **kwargs):
    """Возвращает сгенерированный промпт для отображения"""
    image_visible = dialog_manager.dialog_data["image_visible"]
    return {
        'image_prompt': dialog_manager.dialog_data.get("image_prompt", "Нет промпта"),
        'image_visible': image_visible
    }


@async_log_exception
async def on_use_auto_prompt(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Использование сгенерированного промпта для генерации изображения"""
    data = dialog_manager.dialog_data
    image_prompt = data.get("image_prompt")
    if not image_prompt:
        await callback.message.answer("<b>❌ Сначала сгенерируйте промпт для изображения</b>")
        return
    # Автоматический переход к генерации изображения
    await on_image_prompt(callback.message, widget=None, dialog_manager=dialog_manager, text=image_prompt)


@async_log_exception
async def on_image_prompt(message: Message, widget, dialog_manager: DialogManager, text: str):
    """Получение промпта для изображения и генерация изображения"""
    # Показываем статус генерации
    status_msg = await message.answer("<b>⏳ Генерация изображения...</b>")
    try:
        # Генерация изображения через Yandex.Art
        model_image = conf.yandex.art_model
        image_url = await generate_image(text)
        # Обновляем данные в диалоге
        dialog_manager.dialog_data["image_url"] = image_url
        dialog_manager.dialog_data["image_prompt"] = text
        dialog_manager.dialog_data["model_image"] = model_image
        dialog_manager.dialog_data["generated_at_image"] = datetime_local()
        dialog_manager.dialog_data["status_image"] = GenerationType.SUCCESS
        # Сохраняем пост в БД
        post = await save_post_to_db(dialog_manager.dialog_data)
        # Удаляем статусное сообщение и переходим к просмотру
        await status_msg.delete()
        # Переход к предварительному просмотру
        await dialog_manager.switch_to(states.PostStates.preview)
    except Exception as e:
        # Обновляем данные с ошибкой
        dialog_manager.dialog_data["status_image"] = GenerationType.ERROR
        dialog_manager.dialog_data["error_message"] = str(e)
        await status_msg.edit_text(f"<b>❌ Ошибка при генерации изображения:</b> {e}")


@async_log_exception
async def on_publish(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Публикация поста в группу"""
    data = dialog_manager.dialog_data
    post_text = data.get('post_text', '')
    image_url = data.get('image_url', '')
    if not post_text:
        await callback.message.answer("<b>❌ Сначала сгенерируйте текст</b>")
        return
    try:
        # Публикация поста
        channel_id = conf.tg_bot.channel_id
        message_id = await publish_post_to_group(channel_id, post_text, image_url)
        # Добавляем статус публикации и дату
        data['published'] = True
        data['published_at'] = datetime_local()
        # Сохраняем в БД
        post = await save_post_to_db(data)
        # Формирование ссылки
        if channel_id.startswith("-100"):
            clean_chat_id = channel_id[4:]  # Убираем "-100"
        elif channel_id.startswith("-"):
            clean_chat_id = channel_id[1:]  # Убираем "-"
        else:
            clean_chat_id = channel_id
        post_url = f"https://t.me/c/{clean_chat_id}/{message_id}"
        # Отправка ссылки
        await callback.message.answer(f"<b>✅ Пост успешно опубликован!</b>\n🔗 {post_url}")
        await dialog_manager.done()
    except Exception as e:
        await callback.message.answer(f"<b>❌ Ошибка при публикации:</b> {e}")


@async_log_exception
async def on_schedule_date_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, selected_date: datetime.date):
    """Обработка выбранной даты публикации"""
    dialog_manager.dialog_data["scheduled_date"] = selected_date
    await dialog_manager.switch_to(states.PostStates.waiting_for_schedule_time)


@async_log_exception
async def on_schedule_time_selected(message: Message, widget, dialog_manager: DialogManager, time_str: str):
    """
    Обработка ввода времени публикации
    Поддерживает разделители: : , . ; - _ ж или пробел
    """
    try:
        selected_date = dialog_manager.dialog_data.get("scheduled_date")
        if not selected_date:
            await message.answer("❌ Сначала выберите дату")
            return
        # Очищаем строку от лишних пробелов
        time_str = time_str.strip()
        # Проверяем формат времени с помощью регулярного выражения
        match = re.match(r"^(\d{1,2})[\:\;\ж\.\s,\-_]+(\d{1,2})$", time_str)
        if not match:
            raise ValueError("Некорректный формат времени")
        # Извлечение часов и минут
        hour, minute = map(int, match.groups())
        # Проверка диапазона времени
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Часы или минуты вне допустимого диапазона")
        # Сохраняем отформатированное время для последующего использования
        selected_time = dt_time(hour=hour, minute=minute)
        # Формируем дату и время
        scheduled_datetime = datetime.combine(selected_date, selected_time)
        # Обновляем данные
        dialog_manager.dialog_data["scheduled_at"] = scheduled_datetime
        dialog_manager.dialog_data["is_scheduled"] = True
        # Сохраняем пост и переходим к подтверждению
        post = await save_post_to_db(dialog_manager.dialog_data)
        await dialog_manager.switch_to(states.PostStates.waiting_for_schedule_confirmation)
    except ValueError as e:
        error_msg = str(e)
        if "groups" in error_msg:
            error_msg = "Неверный формат времени.\nПримеры: 14:30, 14 30, 14.30, 14,30, 14;30, 14-30, 14_30"
        elif "диапазона" in error_msg:
            error_msg = "Часы должны быть от 0 до 23, минуты от 0 до 59"
        else:
            error_msg = "Неверный формат времени.\nПримеры: 14:30, 14 30, 14.30, 14,30, 14;30, 14-30, 14_30"
        logger.error(f"Ошибка ввода времени: {error_msg}")
        await message.answer(f"❌ <b>Ошибка:</b> {error_msg}\n\n"
                             f"🕒 <b>Форматы:</b> HH:MM / HH MM / HH.MM / HH,MM / HH;MM / HH-MM / HH_MM")


@async_log_exception
async def on_schedule_click(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Переход к выбору даты публикации"""
    data = dialog_manager.dialog_data
    if not data.get('post_text'):
        await callback.message.answer("<b>❌ Сначала сгенерируйте текст</b>")
        return
    # Передаем post_id в диалог для последующего обновления
    await dialog_manager.switch_to(states.PostStates.waiting_for_schedule_date)


@async_log_exception
async def on_publish_scheduled(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    data = dialog_manager.dialog_data
    scheduled_at = data.get('scheduled_at')
    if not scheduled_at:
        await callback.message.answer("<b>❌ Сначала задайте дату и время</b>")
        return
    try:
        post = await save_post_to_db(data)
        await schedule_post_job(scheduled_at, post.id)
        await dialog_manager.next()
    except Exception as e:
        logger.error(f"Ошибка при запланировании публикации: {e}")
        await callback.message.answer(f"<b>Ошибка при планировании:</b> {e}")


@async_log_exception
async def on_regenerate_themes(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Обработчик нажатия на кнопку 'Обновить темы'"""
    try:
        # Генерация новых тем
        new_themes = await generate_travel_themes(count=10)
        # Обновление глобальных тем
        set_global_themes(new_themes)
        logger.info("🔄 Темы обновлены")
    except Exception as e:
        logger.error(f"⚠️ Ошибка генерации тем: {e}")


@async_log_exception
async def main_getter(dialog_manager: DialogManager, **kwargs):
    data = dialog_manager.dialog_data
    travel_themes = get_global_themes()
    if travel_themes != []:
        dialog_manager.dialog_data['travel_themes'] = travel_themes
        dialog_manager.dialog_data['travel_themes_ok'] = True
    else:
        dialog_manager.dialog_data['travel_themes_ok'] = False
    callback_data = dialog_manager.middleware_data.get('aiogd_original_callback_data')
    if callback_data is not None:
        if TRAVEL_THEMES_ID in callback_data:
            try:
                # Извлечение ID темы из callback_data
                data_after_change_id = int(callback_data.split(f"{TRAVEL_THEMES_ID}:")[1].split(":")[0])
                # Получение списка тем из dialog_data
                travel_themes_objects = dialog_manager.dialog_data.get("travel_themes_objects", [])
                # Поиск темы по ID
                selected_theme = next((theme for theme in travel_themes_objects if theme.id == data_after_change_id), None)
                if selected_theme:
                    dialog_manager.dialog_data['selected_theme'] = selected_theme
                    # Используем текст для генерации поста
                    dialog_manager.dialog_data['text_prompt'] = selected_theme.name
                else:
                    await dialog_manager.event.message.answer("❌ Тема не найдена 3")
            except (IndexError, ValueError) as e:
                await dialog_manager.event.message.answer("❌ Некорректные данные темы")

    if (hasattr(dialog_manager, 'event') and hasattr(dialog_manager.event, 'from_user') and hasattr(dialog_manager.event.from_user, 'id')):
        user_id = dialog_manager.event.from_user.id
        username = dialog_manager.event.from_user.username
        first_name = dialog_manager.event.from_user.first_name
    elif (hasattr(dialog_manager, 'event') and hasattr(dialog_manager.event, 'update') and hasattr(dialog_manager.event.update, 'callback_query')
          and hasattr(dialog_manager.event.update.callback_query, 'from_user') and hasattr(dialog_manager.event.update.callback_query.from_user, 'id')):
        user_id = dialog_manager.event.update.callback_query.from_user.id
        username = dialog_manager.event.update.callback_query.from_user.username
        first_name = dialog_manager.event.update.callback_query.from_user.first_name
    else:
        user_id = ''
        username = ''
        first_name = ''
    dialog_manager.dialog_data['user_id'] = user_id
    post_text = data.get('post_text', '')
    image_url = data.get('image_url', '')

    travel_themes_objects = []
    travel_themes_ok = dialog_manager.dialog_data.get('travel_themes_ok')
    if travel_themes_ok:
        travel_themes = dialog_manager.dialog_data.get('travel_themes', {}).get('themes', [])
        travel_themes_objects = [
            TravelThemesGroup(id=index, name=theme)
            for index, theme in enumerate(travel_themes)
        ]
        dialog_manager.dialog_data['travel_themes_objects'] = travel_themes_objects
    if image_url:
        image_url_media = MediaAttachment(ContentType.PHOTO, path=image_url)
        image_visible = True
    else:
        image_url_media = ''
        image_visible = False
    dialog_manager.dialog_data['image_visible'] = image_visible
    text_scheduled_at = ''
    text_scheduled_at_ok = ''
    scheduled_at = dialog_manager.dialog_data.get("scheduled_at")
    scheduled_at_t = scheduled_at.strftime("%Y-%m-%d %H:%M") if scheduled_at else ''
    if scheduled_at_t is not None:
        text_scheduled_at = f'\n<b>📅 Публикация планируется ☑️ на: {scheduled_at_t}</b>'
        text_scheduled_at_ok = f'\n<b>📅 Публикация запланирована ✅ на: {scheduled_at_t}</b>'
    skip_image = dialog_manager.dialog_data.get('skip_image', False)
    return {
        'username': username or first_name,
        'image_url_media': image_url_media,
        'image_visible': image_visible,
        'post_text': post_text,
        'text_scheduled_at': text_scheduled_at,
        'text_scheduled_at_ok': text_scheduled_at_ok,
        TRAVEL_THEMES_KEY: travel_themes_objects,
        'skip_image_visible': skip_image
    }


@async_log_exception
async def text_getter(dialog_manager: DialogManager, **kwargs):
    post_text = dialog_manager.dialog_data.get('post_text')
    return {
        'post_text': post_text,
    }


@async_log_exception
async def stats_getter(dialog_manager: DialogManager, **kwargs):
    """Getter для окна статистики — возвращает данные о просмотрах, комментариях и реакциях"""
    post_id = dialog_manager.dialog_data.get("post_id")
    views = dialog_manager.dialog_data.get("views", 0)
    comments = dialog_manager.dialog_data.get("comments", 0)
    reactions = dialog_manager.dialog_data.get("reactions", {})
    # Формируем строку с реакциями
    reactions_str = ", ".join([f"{k}: {v}" for k, v in reactions.items()]) if reactions else "Нет данных"
    return {
        "post_id": post_id,
        "views": views,
        "comments": comments,
        "reactions": reactions_str,
    }


@async_log_exception
async def on_view_stats(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Обработчик нажатия на кнопку 'Статистика'"""
    post_id = dialog_manager.dialog_data.get("post_id")
    if not post_id:
        await callback.message.answer("❌ Не удалось определить ID поста")
        return
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Post).where(Post.id == post_id))
        post = result.scalars().first()
        if post:
            dialog_manager.dialog_data["views"] = post.views
            dialog_manager.dialog_data["comments"] = post.comments
            dialog_manager.dialog_data["reactions"] = post.reactions or {}
        else:
            dialog_manager.dialog_data["views"] = 0
            dialog_manager.dialog_data["comments"] = 0
            dialog_manager.dialog_data["reactions"] = {}
    await dialog_manager.switch_to(state=states.PostStates.VIEW_STATS)


# --- Диалог --- #

generate_text_window = Window(
    Const("<b>✅ Сгенерированный текст:</b>\n"),
    Format("{post_text}"),
    Row(
        Back(Const("⬅️ Назад")),
        Next(Const('Далее ➡️'))
    ),
    state=states.PostStates.waiting_for_text_prompt,
    getter=text_getter,
    parse_mode = 'HTML'
)

generate_image_window = Window(
    Const("<b>Введите описание для изображения или сгенерируйте автоматический промпт</b>"),
    TextInput(id="image_prompt", on_success=on_image_prompt),
    Button(Const("🎨 Сгенерировать промпт для изображения"), id="btn_auto_image", on_click=on_generate_image_prompt),
    Row(
        Back(Const("⬅️ Назад")),
        MAIN_MENU_MAIN_BUTTON,
        SwitchTo(text=Const("Пропустить ↘️"), id="btn_skip_image", state=states.PostStates.preview, on_click=on_skip_image, when=~F['image_visible']),
        Next(Const('Далее ➡️'), when='image_visible')
    ),
    state=states.PostStates.waiting_for_image_prompt,
    getter=auto_prompt_getter,
    parse_mode='HTML'
)

auto_prompt_preview_window = Window(
    Const("<b>✅ Промпт для изображения сгенерирован:</b>\n"),
    Format("<code>{image_prompt}</code>"),
    Const("\n<b><em>Используйте сгенерированный промпт для генерации изображения или введите свой</em></b>"),
    Button(Const("📷 Использовать промпт для генерации изображения"), id="use_auto_prompt", on_click=on_use_auto_prompt),
    TextInput(id="image_prompt", on_success=on_image_prompt),
    Row(
        Back(Const("⬅️ Назад")),
        MAIN_MENU_MAIN_BUTTON,
        Next(Const('Далее ➡️'), when='image_visible')
    ),
    state=states.PostStates.preview_auto_prompt,
    getter=auto_prompt_getter,
    parse_mode='HTML'
)

preview_window = Window(
    # Const("Предварительный просмотр поста:"),
    DynamicMedia('image_url_media', when='image_visible'),
    Format("{post_text}"),
    Row(
        Back(Const("⬅️ Назад"), when=~F['skip_image_visible']),
        SwitchTo(text=Const("⬅️ Назад"), id="btn_back_skip_image", state=states.PostStates.waiting_for_image_prompt, when='skip_image_visible'),
        Button(Const("📢 Опубликовать"), id="btn_publish", on_click=on_publish),
    ),
    Row(
        MAIN_MENU_MAIN_BUTTON,
        Button(Const("⏰ Запланировать публикацию"), id="btn_schedule", on_click=on_schedule_click),
    ),
    state=states.PostStates.preview,
    getter=main_getter,
    parse_mode='HTML',
)

schedule_date_window = Window(
    Const("<b>📅 Выберите дату публикации</b>"),
    Calendar(id="schedule_calendar", on_click=on_schedule_date_selected),
    Row(
        Back(Const("⬅️ Назад")),
        MAIN_MENU_MAIN_BUTTON
    ),
    state=states.PostStates.waiting_for_schedule_date,
)

schedule_time_window = Window(
    Const("<b>⏰ Введите время публикации в формате HH:MM <em>(например, 09:30, или просто 9 30)</em></b>"),
    TextInput(id="schedule_time_input", on_success=on_schedule_time_selected),
    Row(
        Back(Const("⬅️ Назад")),
        MAIN_MENU_MAIN_BUTTON
    ),
    state=states.PostStates.waiting_for_schedule_time,
    parse_mode='HTML'
)

schedule_window = Window(
    DynamicMedia('image_url_media', when='image_visible'),
    Format("{post_text}"),
    Format("{text_scheduled_at}"),
    Row(
        SwitchTo(text=Const('⬅️ Изменить дату'), id='btn_edit_date', state=states.PostStates.waiting_for_schedule_date),
        Back(Const("🕒 Изменить время"), id="btn_edit_time")
    ),
    Row(
        MAIN_MENU_MAIN_BUTTON,
        Button(Const("✅ Подтвердить"), id="confirm_schedule", on_click=on_publish_scheduled),
    ),
    state=states.PostStates.waiting_for_schedule_confirmation,
    getter=main_getter,
    parse_mode='HTML',
)

confirmation_window = Window(
    DynamicMedia('image_url_media', when='image_visible'),
    Format("{post_text}"),
    Format("{text_scheduled_at_ok}"),
    MAIN_MENU_MAIN_BUTTON,
    state=states.PostStates.post_confirmation,
    getter=main_getter,
    parse_mode='HTML',
)

main_dialog = Dialog(
    Window(
        Format("👋 Привет, {username}!\n\n"
               "🌟 Я — ваш SMM-эксперт в формате Telegram-бота для создания контента о путешествиях <b>с полной автоматизацией</b> 🌍✈️\n\n"
               "<b>Что я могу:</b>\n"
               "✍️ <em>Сгенерировать текст</em> по вашей теме\n"
               "🖼️ <em>Создать изображение</em> на основе текста\n"
               "📢 <em>Опубликовать пост</em> в группу за несколько кликов\n"
               "⏰ <em>Запланировать публикацию</em> на удобное время\n"
               "📊 <em>Анализировать статистику</em>: просмотры, реакции\n\n"
               "<b>Выберите тему путешествия или введите свою</b> (например, <code>Путешествие в Таиланд</code>) — и я сделаю всё остальное!"),
        Column(
            Radio(
                checked_text=Format('✅ {item.name}'),
                unchecked_text=Format('{item.name}'),
                id=TRAVEL_THEMES_ID,
                items=TRAVEL_THEMES_KEY,
                item_id_getter=lambda item: item.id,
                on_click=on_text_prompt_callback
            ),
        ),
        TextInput(id="text_prompt", on_success=on_text_prompt),
        Button(Const("❇️ 🔄 ОБНОВИТЬ ТЕМЫ"), id="btn_regenerate_themes", on_click=on_regenerate_themes),
        Start(Const("❇️ 📅 АВТОПЛАНИРОВАНИЕ"), id="btn_auto_schedule", state=states.AutoScheduleStates.PERIOD_SELECT),
        Start(Const("❇️ 📜 ПОСМОТРЕТЬ ЗАПЛАНИРОВАННЫЕ"), id="btn_view_scheduled", state=states.ScheduledPostsStates.SCHEDULED_POSTS_VIEW),
        Start(Const("❇️ 📊 СТАТИСТИКА"), id="btn_stats", state=states.StatsStates.STATS_VIEW),
        state=states.PostStates.MAIN,
        getter=main_getter,
        parse_mode='HTML'
    ),
    generate_text_window,
    generate_image_window,
    auto_prompt_preview_window,
    preview_window,
    schedule_date_window,
    schedule_time_window,
    schedule_window,
    confirmation_window
)
