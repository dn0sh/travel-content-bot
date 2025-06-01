# database/models.py
from enum import Enum as PyEnum
from sqlalchemy import Boolean, BigInteger, Column, DateTime, Enum, Integer, JSON, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from config.env import conf, datetime_local
from config.logging_config import async_log_exception

# Асинхронный движок
engine = create_async_engine(conf.db.DB_URI, future=True)
# Базовый класс для моделей
Base = declarative_base()


# Перечисление для типа генерации
class GenerationType(PyEnum):
    SUCCESS = "success"
    ERROR = "error"


class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True, doc="Уникальный идентификатор поста")
    # Текст поста
    text_prompt = Column(String, doc="Промпт, использованный для генерации текста")
    text = Column(String, doc="Сгенерированный текст поста")
    model_text = Column(String, doc="Модель ИИ, использованная для генерации текста")
    generated_at_text = Column(DateTime, default=datetime_local(), doc="Дата и время генерации текста")
    status_text = Column(Enum(GenerationType), default=GenerationType.SUCCESS, doc="Статус генерации текста (success/error)")
    # Изображение
    image_path = Column(String, doc="Путь к сгенерированному изображению")
    image_prompt = Column(String, doc="Промпт, использованный для генерации изображения")
    model_image = Column(String, doc="Модель ИИ, использованная для генерации изображения")
    generated_at_image = Column(DateTime, default=datetime_local(), doc="Дата и время генерации изображения")
    status_image = Column(Enum(GenerationType), default=GenerationType.SUCCESS, doc="Статус генерации изображения (success/error)")
    # Планирование публикации
    is_scheduled = Column(Boolean, default=False, doc="Флаг: пост запланирован на публикацию")
    scheduled_at = Column(DateTime, doc="Дата и время запланированной публикации")
    # Публикация
    published = Column(Boolean, default=False, doc="Флаг: пост опубликован")
    published_at = Column(DateTime, doc="Дата и время публикации поста")
    # Статистика
    views = Column(BigInteger, default=0, doc="Количество просмотров поста")
    comments = Column(Integer, default=0, doc="Количество комментариев под постом")
    reactions = Column(JSON, default={}, doc="Реакции на пост в формате JSON")
    # Дополнительно
    created_at = Column(DateTime, default=datetime_local(), doc="Дата создания записи")
    error_message = Column(String, doc="Сообщение об ошибке (если статус = ERROR)")
    message_id = Column(Integer, doc="ID сообщения в Telegram для прямой ссылки на пост")


class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, doc="Уникальный идентификатор администратора")
    user_id = Column(Integer, unique=True, doc="Telegram ID пользователя, который является администратором")


# Создаем асинхронную сессию для взаимодействия с базой данных
AsyncSessionLocal = async_sessionmaker(
    bind=engine,  # Привязка сессии к базе данных
    class_=AsyncSession,  # Использование асинхронных сессий
    autoflush=True,  # Автоматический сброс изменений
    expire_on_commit=False  # Не удалять данные из сессии после фиксации (Данные не "истекают" после коммита)
)


@async_log_exception
async def init_db():
    """
    Инициализация базы данных
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
