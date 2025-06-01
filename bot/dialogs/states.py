# bot/dialogs/states.py
from aiogram.fsm.state import State, StatesGroup

class PostStates(StatesGroup):
    MAIN = State()  # Основное меню
    waiting_for_text_prompt = State()  # Ввод текстового промпта
    preview_auto_prompt = State()
    waiting_for_image_prompt = State()  # Ввод промпта для изображения
    preview = State()  # Предварительный просмотр
    waiting_for_schedule_date = State()  # Выбор даты публикации
    waiting_for_schedule_time = State()  # Ввод времени публикации
    waiting_for_schedule_confirmation = State()
    post_confirmation = State()


class AutoScheduleStates(StatesGroup):
    PERIOD_SELECT = State()       # Выбор периода
    DAILY_POSTS_SELECT = State()  # Выбор количества постов в день
    TIME_SELECT = State()         # Выбор времени публикации
    SELECT_START_DATE = State()
    THEMES_SELECT = State()       # Выбор тем
    CUSTOM_THEME = State()        # Добавление пользовательской темы
    SCHEDULE_PREVIEW = State()    # Предварительный просмотр расписания
    SCHEDULE_CONFIRMATION = State()  # Подтверждение расписания


class ScheduledPostsStates(StatesGroup):
    SCHEDULED_POSTS_VIEW = State()  # Просмотр запланированных постов


class StatsStates(StatesGroup):
    STATS_VIEW = State()  # Просмотр статистики постов
