# bot/dialogs/auto_schedule.py
import math
import re
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager, StartMode
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Row, Calendar, Column, Multiselect, Next, Back, Select, SwitchTo
from aiogram_dialog.widgets.text import Const, Format, List as DList
from dataclasses import dataclass
from datetime import datetime, timedelta, time as dt_time
from typing import Any, Dict

from bot.dialogs import states
from bot.themes import get_global_themes, set_global_themes
from config.config import generate_travel_themes, generate_text, generate_image_prompt, get_current_model
from config.env import bot_global, conf, datetime_local
from config.logging_config import logger, async_log_exception
from database.models import GenerationType, Post, AsyncSessionLocal
from yandex_art.client import generate_image
from scheduler.jobs import schedule_post_job
from .common import MAIN_MENU_MAIN_BUTTON


# Константы для периодов
PERIOD_OPTIONS = {
    "2 дня": ("2 дня", 2),
    "неделя": ("Неделя", 7),
    "10 дней": ("10 дней", 10),
    "месяц": ("Месяц", 30)
}

# Константы для интерфейса
MAX_THEMES = 35
MAX_DAILY_POSTS = 1
DEFAULT_DAILY_POSTS = 1
DEFAULT_TIME = "09:30"
TRAVEL_THEMES_KEY = 'key_themes'
TRAVEL_THEMES_ID = 'themes_select'
MAX_UPDATE_INTERVAL = 5  # секунды между обновлениями сообщения


@dataclass
class TravelThemesGroup:
    id: int
    name: str


@async_log_exception
async def start_auto_schedule(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Инициализация начальных данных"""
    dialog_manager.dialog_data.update({
        'period': None,
        'daily_posts': DEFAULT_DAILY_POSTS,
        'publish_time': DEFAULT_TIME,
        'start_date': None,
        'themes': [],
        'custom_themes': [],
        'total_posts': 0,
        'scheduled_posts': []
    })
    # Загружаем стандартные темы
    if not dialog_manager.dialog_data.get('themes'):
        themes = get_global_themes().get('themes', [])
        dialog_manager.dialog_data['themes'] = themes[:MAX_THEMES]
    await dialog_manager.start(state=states.AutoScheduleStates.PERIOD_SELECT, mode=StartMode.RESET_STACK)


@async_log_exception
async def auto_schedule_getter(dialog_manager: DialogManager, **kwargs):
    """Получатель данных для окон"""
    data = dialog_manager.dialog_data
    # Рассчитываем количество дней в периоде
    period = data.get('period')
    if period is None:
        # dialog_manager.dialog_data['period'] = '1 день'
        period_days = 1
        period_days_text = 1
    else:
        period_days = int(PERIOD_OPTIONS[period][1]) if period else 1  # конвертация в int
        period_days_text = period
    dialog_manager.dialog_data['period_days'] = period_days
    # Рассчитываем количество постов в день
    daily_posts = int(data.get('daily_posts', DEFAULT_DAILY_POSTS))  # конвертация в int
    dialog_manager.dialog_data['daily_posts'] = daily_posts
    total_posts = daily_posts * period_days
    dialog_manager.dialog_data['total_posts'] = total_posts
    # Получаем выбранные темы
    themes = data.get('themes', [])
    # Получаем темы из глобального хранилища
    global_themes = get_global_themes()
    travel_themes = {}
    if isinstance(global_themes, dict):
        travel_themes = global_themes.get('themes', [])
    custom_themes = data.get('custom_themes', [])
    # Убедимся, что это список
    if not isinstance(themes, list):
        themes = []
    if not isinstance(travel_themes, list):
        travel_themes = []
    if not isinstance(custom_themes, list):
        custom_themes = []
        dialog_manager.dialog_data['custom_themes'] = custom_themes
    # all_themes = travel_themes + themes + custom_themes # TODO
    all_themes = travel_themes + custom_themes # TODO
    dialog_manager.dialog_data['all_themes'] = all_themes
    # Рассчитываем примерное время публикации
    schedule_preview = []
    publish_time = data.get('publish_time', '09:30')
    dialog_manager.dialog_data['publish_time'] = publish_time
    travel_themes_objects = [
        TravelThemesGroup(id=index, name=theme)
        for index, theme in enumerate(all_themes)
    ]
    selected_theme_indices = dialog_manager.dialog_data.get('selected_theme_indices', [])
    selected_theme_names = dialog_manager.dialog_data.get('selected_theme_names', [])
    if publish_time:
        start_date = data.get('start_date') or (datetime_local().date() + timedelta(days=1))
        if data.get('start_date') is None:
            dialog_manager.dialog_data['start_date'] = start_date
        try:
            hour, minute = map(int, publish_time.split(":"))
            base_time = dt_time(hour=hour, minute=minute)
            for day in range(period_days):
                current_date = start_date + timedelta(days=day)
                for post_num in range(daily_posts):
                    scheduled_datetime = datetime.combine(current_date, base_time) + timedelta(minutes=post_num)
                    theme_index = (day * daily_posts + post_num) % len(selected_theme_names) if selected_theme_names else 0
                    theme = selected_theme_names[theme_index] if selected_theme_names else "..."
                    schedule_preview.append({
                        'date': scheduled_datetime.strftime("%Y-%m-%d"),
                        'time': scheduled_datetime.strftime("%H:%M"),
                        'theme': theme
                    })
        except Exception as e:
            logger.error(f"302.99 Ошибка при расчете расписания: {e}")
    return {
        'period': period_days_text,
        'daily_posts': daily_posts,
        'publish_time': data.get('publish_time', DEFAULT_TIME),
        'start_date': data.get('start_date'),
        'themes': themes,
        'custom_themes': custom_themes,
        'total_posts': total_posts,
        'schedule_preview': schedule_preview,
        'themes_count': len(all_themes),
        'max_themes': MAX_THEMES,
        'max_daily_posts': MAX_DAILY_POSTS,
        'selected_themes_count': len(selected_theme_indices),
        'selected_themes_count_ok': '✅' if not len(selected_theme_indices) < total_posts else '',
        'selected_themes_visible': True if len(selected_theme_indices) !=0 else False,
        TRAVEL_THEMES_KEY: travel_themes_objects
    }


@async_log_exception
async def on_period_selected(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager, selected_period: str):
    """Обработчик выбора периода"""
    dialog_manager.dialog_data['period'] = selected_period
    await dialog_manager.next()


@async_log_exception
async def on_daily_posts_selected(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager, selected_posts: int):
    """Обработчик выбора количества постов в день"""
    dialog_manager.dialog_data['daily_posts'] = selected_posts
    await dialog_manager.next()


@async_log_exception
async def on_time_selected(message: Message, widget: Any, dialog_manager: DialogManager, time_str: str):
    """Обработчик ввода времени публикации"""
    try:
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
        # Сохраняем отформатированное время
        formatted_time = f"{hour:02d}:{minute:02d}"
        dialog_manager.dialog_data['publish_time'] = formatted_time
        await dialog_manager.next()
    except ValueError as e:
        error_msg = str(e)
        if "groups" in error_msg:
            error_msg = "Неверный формат времени.\nПримеры: 14:30, 14 30, 14.30, 14,30, 14;30, 14-30, 14_30"
        elif "диапазона" in error_msg:
            error_msg = "Часы должны быть от 0 до 23, минуты от 0 до 59"
        else:
            error_msg = "Неверный формат времени.\nПримеры: 14:30, 14 30, 14.30, 14,30, 14;30, 14-30, 14_30"
        logger.error(f"Ошибка ввода времени: {error_msg}")
        await message.answer(f"❌ <b>Ошибка:</b> {error_msg}\n"
                             f"🕒 <b>Форматы:</b> HH:MM / HH MM / HH.MM / HH,MM / HH;MM / HH-MM / HH_MM")

@async_log_exception
async def on_start_date_selected(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager, selected_date: datetime.date):
    """Обработчик выбора даты начала"""
    dialog_manager.dialog_data['start_date'] = selected_date
    await dialog_manager.next()

	
@async_log_exception
async def on_theme_selected(callback: CallbackQuery, button: Button, dialog_manager: DialogManager, selected_button):
    """Обработчик выбора темы"""
    try:
        # Извлечение индекса темы из кнопки
        theme_index = int(selected_button.replace("theme_", ""))  # Например, "theme_0" → 0
        # Получаем список всех доступных тем
        all_themes = dialog_manager.dialog_data.get('all_themes', [])
        if not all_themes:
            await callback.message.answer("❌ Темы не загружены")
            return
        # Получаем список индексов выбранных тем
        selected_theme_indices = dialog_manager.dialog_data.get('selected_theme_indices', [])
        # Добавляем или убираем тему
        if theme_index in selected_theme_indices:
            selected_theme_indices.remove(theme_index)
        else:
            if len(selected_theme_indices) >= MAX_THEMES:
                await callback.message.answer(f"⚠️ Максимум {MAX_THEMES} тем можно выбрать")
                return
            selected_theme_indices.append(theme_index)
        # Сохраняем обновленный список индексов
        dialog_manager.dialog_data['selected_theme_indices'] = selected_theme_indices
        # Получаем названия выбранных тем
        selected_theme_names = [all_themes[i] for i in selected_theme_indices if i < len(all_themes)]
        dialog_manager.dialog_data['selected_theme_names'] = selected_theme_names
    except (ValueError, IndexError) as e:
        error_msg = f"Некорректный выбор темы: {str(e)}"
        logger.error(error_msg)
        await callback.message.answer(f"❌ Ошибка выбора темы: {error_msg}")
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при выборе темы: {e}")
        await callback.message.answer(f"❌ Ошибка выбора темы: {str(e)}")


@async_log_exception
async def on_add_custom_theme(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Обработчик добавления пользовательской темы"""
    await dialog_manager.next()


@async_log_exception
async def on_save_custom_theme(message: Message, widget: Any, dialog_manager: DialogManager, theme_text: str):
    """Обработчик сохранения пользовательской темы"""
    custom_themes = dialog_manager.dialog_data.get('custom_themes', [])
    if len(custom_themes) >= MAX_THEMES:
        await message.answer(f"❌ Достигнут максимальный лимит пользовательских тем: {MAX_THEMES}")
        return
    theme_text = theme_text.strip()
    if theme_text:
        custom_themes.append(theme_text)
        dialog_manager.dialog_data['custom_themes'] = custom_themes
        await message.answer(f"✅ Тема добавлена: {theme_text}")
    await dialog_manager.back()


@async_log_exception
async def on_remove_custom_theme(callback: CallbackQuery, button: Button, dialog_manager: DialogManager, index: int):
    """Обработчик удаления пользовательской темы"""
    custom_themes = dialog_manager.dialog_data.get('custom_themes', [])
    if 0 <= index < len(custom_themes):
        removed_theme = custom_themes.pop(index)
        dialog_manager.dialog_data['custom_themes'] = custom_themes
        await callback.message.answer(f"🗑️ Тема удалена: {removed_theme}")


@async_log_exception
async def on_generate_themes(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Обработчик генерации новых тем"""
    try:
        # Получаем общее количество требуемых тем
        total_posts = dialog_manager.dialog_data.get('total_posts', 10)
        if total_posts <= 0:
            await callback.message.answer("⚠️ Количество тем должно быть больше 0")
            return
        # Вычисляем количество тем с запасом (на 47% больше), но не менее 5
        new_theme_count = max(math.ceil(total_posts * 1.47), 5)
        # Подготавливаем списки для хранения результатов
        all_themes = []
        remaining_posts = new_theme_count  # Теперь генерируем с запасом
        # Генерируем темы порциями по 15
        while remaining_posts > 0:
            # Определяем количество тем для текущей генерации
            current_count = min(remaining_posts, 15)
            # Генерируем темы
            new_themes = await generate_travel_themes(count=current_count)
            # Добавляем новые темы в общий список
            if new_themes and "themes" in new_themes:
                all_themes.extend(new_themes["themes"])
            # Уменьшаем счетчик оставшихся постов
            remaining_posts -= current_count
        # Обновляем глобальные темы
        set_global_themes({"themes": all_themes})
        # Обновление тем в диалоге
        dialog_manager.dialog_data['themes'] = all_themes
        dialog_manager.dialog_data['selected_theme_indices'] = []
        dialog_manager.dialog_data['selected_theme_names'] = []
        logger.info(f"🔄 Темы обновлены: {len(all_themes)} шт.")
        # await callback.message.answer(f"✅ Сгенерировано {len(all_themes)} тем (запрошено: {new_theme_count})")
    except Exception as e:
        error_msg = f"⚠️ Ошибка генерации тем: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await callback.message.answer(error_msg)


@async_log_exception
async def on_preview_schedule(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Обработчик перехода к предварительному просмотру"""
    await dialog_manager.next()


@async_log_exception
async def on_confirm_schedule(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Обработчик подтверждения расписания"""
    data = dialog_manager.dialog_data
    required_fields = ['daily_posts', 'start_date', 'publish_time', 'selected_theme_names']
    if not all(data.get(field) for field in required_fields):
        await callback.message.answer("❌ Не все параметры заданы. Пожалуйста, заполните все поля.")
        return
    status_msg = await callback.message.answer("<b>⏳ Начинаю генерацию и планирование постов...</b>")
    status_message_id = status_msg.message_id
    dialog_manager.dialog_data['status_message_id'] = status_message_id
    try:
        # Передаем message_id в функцию
        await generate_and_schedule_posts(
            data=data,
            status_message_id=status_message_id,
            chat_id=callback.message.chat.id
        )
        await callback.message.bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=status_message_id,
            text="<b>✅ Все посты успешно запланированы!</b>"
        )
    except Exception as e:
        # Обновляем статусное сообщение об ошибкой
        await callback.message.bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=status_message_id,
            text=f"<b>❌ Ошибка при планировании: {str(e)}</b>"
        )
        logger.error(f"Ошибка при подтверждении расписания: {e}", exc_info=True)
    # Возвращаемся в главное меню
    await dialog_manager.done()


@async_log_exception
async def generate_and_schedule_posts(data: Dict[str, Any], status_message_id: int, chat_id: int):
    """Генерация постов и планирование их публикации"""
    selected_theme_names = data['selected_theme_names']
    model_text = await get_current_model()
    daily_posts = data['daily_posts']
    publish_time = data['publish_time']
    start_date = data.get('start_date') or datetime_local().date()
    period_days = data['period_days']
    hour, minute = map(int, publish_time.split(":"))
    base_time = dt_time(hour=hour, minute=minute)
    total_posts = period_days * daily_posts
    posts_scheduled = 0
    last_update_time = datetime.now()
    for day in range(period_days):
        current_date = start_date + timedelta(days=day)
        for post_num in range(daily_posts):
            # Рассчитываем дату и время публикации
            scheduled_datetime = datetime.combine(current_date, base_time) + timedelta(minutes=post_num)  # Смещение на минуты для уникальности
            # Выбираем тему
            theme = selected_theme_names[(day * daily_posts + post_num) % len(selected_theme_names)]
            try:
                # Генерируем текст поста
                post_text = await generate_text(theme)
                # Генерируем изображение
                image_prompt = await generate_image_prompt(post_text)
                image_path = await generate_image(image_prompt)
                # Сохраняем пост в БД
                async with AsyncSessionLocal() as session:
                    post = Post(
                        text=post_text,
                        text_prompt=theme,
                        model_text=model_text,
                        image_path=image_path,
                        image_prompt=image_prompt,
                        model_image=conf.yandex.art_model,
                        scheduled_at=scheduled_datetime,
                        is_scheduled=True,
                        status_text=GenerationType.SUCCESS,
                        status_image=GenerationType.SUCCESS
                    )
                    session.add(post)
                    await session.commit()
                    await session.refresh(post)
                    # Планируем публикацию
                    await schedule_post_job(scheduled_datetime, post.id)
                posts_scheduled += 1
                now = datetime.now()
                if (now - last_update_time).total_seconds() > MAX_UPDATE_INTERVAL:
                    await bot_global.edit_message_text(chat_id=chat_id, message_id=status_message_id, text=f"⏳ Пост {posts_scheduled} из {total_posts} запланирован...")
                    last_update_time = now
                logger.info(f"Запланирован пост {post.id} на {scheduled_datetime}")
            except Exception as e:
                logger.error(f"Ошибка генерации поста для темы {theme}: {e}")
                continue


# --- Окна диалога --- #

# Окно выбора периодичности
select_period_window = Window(
    Const("<b>📅 Выберите период планирования:</b>"),
    Select(
        text=Format("{item[0]}"),
        id="period_select",
        item_id_getter=lambda x: x[1],
        items=[
            ("На 2 дня", "2 дня"),
            ("На неделю", "неделя"),
            ("На 10 дней", "10 дней"),
            ("На месяц", "месяц")
        ],
        on_click=on_period_selected
    ),
    Row(
        MAIN_MENU_MAIN_BUTTON,
        Next(Const('Далее ➡️')),
    ),
    state=states.AutoScheduleStates.PERIOD_SELECT
)

# Окно выбора количества постов в день
select_daily_posts_window = Window(
    Const("<b>🔢 Выберите количество постов в день:</b>"),
    Select(
        text=Format("{item}"),
        id="daily_posts_select",
        item_id_getter=lambda x: x,
        items=list(range(1, MAX_DAILY_POSTS + 1)),
        on_click=on_daily_posts_selected
    ),
    Row(
        Back(Const("⬅️ Назад")),
        Next(Const('Далее ➡️'))
    ),
    state=states.AutoScheduleStates.DAILY_POSTS_SELECT
)

# Окно выбора времени публикации
select_time_window = Window(
    Const("<b>⏰ Введите время публикации в формате HH:MM (например, 09:30)</b>"),
    TextInput(id="time_input", on_success=on_time_selected),
    Row(
        Back(Const("⬅️ Назад")),
        Next(Const('Далее ➡️'))
    ),
    state=states.AutoScheduleStates.TIME_SELECT
)

# Окно выбора даты начала
select_start_date_window = Window(
    Const("<b>📅 Выберите дату начала планирования:</b>"),
    Calendar(id="start_date_calendar", on_click=on_start_date_selected),
    Row(
        Back(Const("⬅️ Назад")),
        Next(Const('Далее ➡️'))
    ),
    state=states.AutoScheduleStates.SELECT_START_DATE
)

# Окно выбора тем
select_themes_window = Window(
    Const("<b>🧩 Выберите темы для автоматической генерации</b>:"),
    Format("Всего тем предложено: {themes_count}"),
    Format("Нужно выбрать: {total_posts}"),
    Format("Выбрано: {selected_themes_count} {selected_themes_count_ok}"),
    Column(
        Multiselect(
            checked_text=Format('✅ {item.name}'),
            unchecked_text=Format('{item.name}'),
            id=TRAVEL_THEMES_ID,
            items=TRAVEL_THEMES_KEY,
            item_id_getter=lambda item: item.id,
            on_click=on_theme_selected
        )
    ),
    Row(
        Button(Const("➕ Добавить свою тему"), id="btn_add_custom_theme", on_click=on_add_custom_theme),
        Button(Const("🔄 Обновить темы"), id="btn_regenerate_themes", on_click=on_generate_themes)
    ),
    Row(
        Back(Const("⬅️ Назад")),
        SwitchTo(text=Const('➡️ Далее'), id='btn_edit_date', state=states.AutoScheduleStates.SCHEDULE_PREVIEW, when='selected_themes_visible'),
    ),
    state=states.AutoScheduleStates.THEMES_SELECT,
    getter=auto_schedule_getter,
    parse_mode = 'HTML'
)

# Окно добавления пользовательской темы
add_custom_theme_window = Window(
    Const("<b>Введите вашу тему:</b>"),
    TextInput(id="custom_theme_input", on_success=on_save_custom_theme),
    Row(
        Back(Const("⬅️ Назад")),
        Next(Const('Далее ➡️'))
    ),
    state=states.AutoScheduleStates.CUSTOM_THEME
)

# Окно предварительного просмотра расписания
preview_schedule_window = Window(
    Const('<b>📋 Предварительный просмотр расписания:</b>'),
    Format("Период: <b>{period}</b>\n"
           "Постов в день: <b>{daily_posts}</b>\n"
           "Время публикации: <b>{publish_time}</b>\n"
           # "Количество тем: <b>{themes_count}</b>\n"
           "Всего постов: <b>{total_posts}</b>"),
    Const("\n<b>📅 Примерное расписание публикации:</b>"),
    # Отображение списка расписания
    DList(
        field=Format("{item[date]} {item[time]}\n{item[theme]}\n"),  # Формат элемента
        items="schedule_preview",  # Ключ в getter-е, возвращающий список
        sep="\n",  # Разделитель между элементами
    ),
    Row(
        SwitchTo(text=Const('⬅️ Назад'), id='btn_edit_date', state=states.AutoScheduleStates.THEMES_SELECT),
        Button(Const("🚀 Запустить планирование"), id="btn_confirm", on_click=on_confirm_schedule)
    ),
    state=states.AutoScheduleStates.SCHEDULE_PREVIEW,
    getter=auto_schedule_getter,
    parse_mode='HTML'
)

# --- Основной диалог --- #
auto_schedule_dialog = Dialog(
    select_period_window,
    select_time_window,
    select_start_date_window,
    select_themes_window,
    add_custom_theme_window,
    preview_schedule_window
)
