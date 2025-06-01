# config/logging_config.py
import logging
import logging.handlers
import os
import datetime
import traceback
from functools import wraps
from config.env import conf

# === Настройки логирования ===
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_logs")
os.makedirs(LOG_DIR, exist_ok=True)

# === Формат логов ===
LOG_FORMAT = '%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s'
formatter = logging.Formatter(LOG_FORMAT)

# === Создание корневого логгера ===
logger = logging.getLogger()
logger.setLevel(getattr(logging, conf.tg_bot.LOG_LEVEL, logging.INFO))

# === Удаление существующих хэндлеров (чтобы избежать дублирования) ===
logger.handlers.clear()

# === Хэндлер: вывод в консоль ===
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# === Хэндлер: запись в файл с ротацией ===
log_file_path = os.path.join(LOG_DIR, f"{datetime.datetime.now().strftime('%Y-%m-%d')}_log.txt")
file_handler = logging.handlers.TimedRotatingFileHandler(
    filename=log_file_path,
    when="midnight",
    interval=1,
    backupCount=10,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# === Логирование ошибок в отдельные файлы с traceback ===
def log_exception(func):
    """Декоратор для логирования исключений в обычных функциях"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            current_function = func.__name__
            log_filename = datetime.datetime.now().strftime(f"%Y-%m-%d_%H-%M-%S {current_function}.traceback")
            error_path = os.path.join(LOG_DIR, log_filename)

            error_handler = logging.FileHandler(error_path, encoding='utf-8')
            error_handler.setFormatter(formatter)
            logger.addHandler(error_handler)

            logger.error(f"▼ ▼ ▼ ▼ ▼ traceback: Ошибка в {current_function}  ▼ ▼ ▼ ▼ ▼")
            logger.error(f"traceback: Исключение в функции {current_function}: {e}\n{traceback.format_exc()}")
            logger.error(f"▲ ▲ ▲ ▲ ▲ traceback: Ошибка в {current_function}  ▲ ▲ ▲ ▲ ▲")

            logger.removeHandler(error_handler)

            raise e
    return wrapper


def async_log_exception(func):
    """Декоратор для асинхронных функций"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            current_function = func.__name__
            log_filename = datetime.datetime.now().strftime(f"%Y-%m-%d_%H-%M-%S {current_function}.traceback")
            error_path = os.path.join(LOG_DIR, log_filename)

            error_handler = logging.FileHandler(error_path, encoding='utf-8')
            error_handler.setFormatter(formatter)
            logger.addHandler(error_handler)

            logger.error(f"▼ ▼ ▼ ▼ ▼ traceback: Ошибка в {current_function}  ▼ ▼ ▼ ▼ ▼")
            logger.error(f"traceback: Исключение в функции {current_function}: {e}\n{traceback.format_exc()}")
            logger.error(f"▲ ▲ ▲ ▲ ▲ traceback: Ошибка в {current_function}  ▲ ▲ ▲ ▲ ▲")

            logger.removeHandler(error_handler)

            raise e
    return wrapper


# === Логирование сторонних модулей ===
try:
    import sqlalchemy
    sqlalchemy_logger = logging.getLogger('sqlalchemy')
    sqlalchemy_logger.setLevel(logger.level)
    sqlalchemy_logger.addHandler(file_handler)
    sqlalchemy_logger.addHandler(console_handler)
except ImportError:
    logger.info("Модуль sqlalchemy не найден, логирование пропущено")

try:
    import aiosqlite
    aiosqlite_logger = logging.getLogger('aiosqlite')
    aiosqlite_logger.setLevel(logger.level)
    aiosqlite_logger.addHandler(file_handler)
    aiosqlite_logger.addHandler(console_handler)
except ImportError:
    logger.info("Модуль aiosqlite не найден, логирование пропущено")

try:
    import openai
    openai_logger = logging.getLogger('openai')
    openai_logger.setLevel(logger.level)
    openai_logger.addHandler(file_handler)
    openai_logger.addHandler(console_handler)
except ImportError:
    logger.info("Модуль openai не найден, логирование пропущено")

# === Вспомогательная функция для инициализации логирования ===
def setup_logging(level=None):
    """
    Применяет настройки логирования.
    Можно вызвать один раз при старте приложения.
    """
    if level is not None:
        logger.setLevel(level)
    logger.info("Логирование настроено")