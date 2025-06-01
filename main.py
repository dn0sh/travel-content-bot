# main.py
from aiogram import Dispatcher, F, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, Message
from aiogram_dialog import DialogManager, setup_dialogs, StartMode
from datetime import datetime, timedelta
from config.config import generate_travel_themes
from config.env import bot_global, conf
from config.logging_config import logging, setup_logging, logger, async_log_exception
from database.models import init_db
from bot.dialogs import states
from bot.dialogs.generate_post import main_dialog
from bot.dialogs.auto_schedule import auto_schedule_dialog
from bot.dialogs.scheduled_posts import scheduled_posts_dialog
from bot.dialogs.post_stats import post_stats_dialog
from bot.themes import set_global_themes
from scheduler.jobs import scheduler, setup_stats_job

# Настройка логирования
setup_logging(level=logging.DEBUG)  # Инициализация логирования

# Список команд для меню бота
COMMANDS = {
    "start": "Запустить бот"
}

# Создаем роутер для управления callback-запросами
router = Router()
# Добавляем диалоги aiogram_dialog в роутер
router.include_routers(
    main_dialog,
    auto_schedule_dialog,
    scheduled_posts_dialog,
    post_stats_dialog,
)

# === Логирование стартовых действий ===
logger.info("🚀 Запуск бота: Инициализация модулей")

@async_log_exception
async def on_start(message: Message, dialog_manager: DialogManager):
    """Обработчик команды /start"""
    username = message.from_user.username or message.from_user.full_name
    logger.info(f"👋 Пользователь {username} запустил бота")
    await dialog_manager.start(state=states.PostStates.MAIN, mode=StartMode.RESET_STACK)


@async_log_exception
async def set_main_menu():
    """Настройка кнопки меню бота и его команд"""
    try:
        main_menu_commands = [
            BotCommand(command=command, description=description)
            for command, description in COMMANDS.items()
        ]
        await bot_global.set_my_commands(main_menu_commands)
        logger.debug("✅ Команды бота успешно установлены")
    except Exception as e:
        logger.exception(f"❌ Ошибка установки команд: {e}")


@async_log_exception
async def setup_handlers(dp: Dispatcher):
    """Регистрация обработчиков событий"""
    dp.message.register(on_start, F.text == '/start')
    logger.debug("🧠 Обработчики событий зарегистрированы")


@async_log_exception
async def start_scheduler():
    """Запуск планировщика задач"""
    try:
        scheduler.add_job(generate_travel_themes_job, 'date', run_date=datetime.now() + timedelta(seconds=5))
        await setup_stats_job()  # Добавляем задачу обновления статистики
        scheduler.start()
        logger.debug(f"⏰ Планировщик запущен. Текущие задачи: {scheduler.get_jobs()}")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска планировщика: {e}")


@async_log_exception
async def generate_travel_themes_job():
    # Генерация тем при старте бота
    logger.debug("⏰ Выполняю задачу генерации тем")
    initial_themes = await generate_travel_themes(count=4)
    set_global_themes(initial_themes)
    logger.debug(f"🎯 Сгенерировано {len(initial_themes)} тем для путешествий")


@async_log_exception
async def stop_scheduler():
    """Остановка планировщика при завершении работы"""
    if scheduler.running:
        scheduler.shutdown()
        logger.debug("💤 Планировщик остановлен")


@async_log_exception
async def main():
    """Основная функция запуска бота"""
    try:
        # Инициализация БД
        await init_db()
        logger.debug("🗄️ База данных инициализирована")
        # Инициализация диспетчера
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        conf.dp = dp  # Сохраняем диспетчер в конфиге для дальнейшего использования
        # Подключение диалогов и обработчиков
        dp.include_router(router)
        setup_dialogs(dp)
        # Регистрация команд
        dp.startup.register(set_main_menu)
        await setup_handlers(dp)
        # Запуск планировщика
        await start_scheduler()
        # Запуск бота
        logger.info("🟢 Бот готов к работе")
        await dp.start_polling(bot_global, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.critical(f"💀 Критическая ошибка при запуске бота: {e}")
    finally:
        await stop_scheduler()
        logger.info("🛑 Работа бота завершена")


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
