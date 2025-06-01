# bot/dialogs/post_stats.py
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import Dialog, Window, DialogManager, StartMode
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Row, FirstPage, PrevPage, CurrentPage, NextPage, LastPage, StubScroll
from aiogram_dialog.widgets.media import DynamicMedia
from bot.dialogs import states
from sqlalchemy.future import select
from database.models import Post, AsyncSessionLocal
from config.logging_config import logger
from .common import MAIN_MENU_MAIN_BUTTON

DEFAULT_PAGER_ID = '__pager__'
ID_SCROLL_WITH_PAGER = 'scroll_with_pager'


# --- Getter ---
async def stats_getter(dialog_manager, **kwargs):
    """Возвращает данные о статистике опубликованных постов"""
    current_page = await dialog_manager.find(ID_SCROLL_WITH_PAGER).get_page()
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Post)
                .where(Post.published == True)
                .order_by(Post.published_at.desc())
            )
            posts = result.scalars().all()
            if not posts:
                return {
                    'pages': 0,
                    'current_page': current_page,
                    'user_group_have_access': '<b><em>Нет опубликованных постов</em></b>',
                    'post_text': '',
                    'image_url_media': '',
                    'image_visible': False,
                    'button_visible': False,
                }
            page_size = 1  # 1 пост на страницу
            pages = (len(posts) + page_size - 1) // page_size
            start = current_page * page_size
            end = start + page_size
            post = posts[start:end][0] if start < len(posts) else None
            if not post:
                return {
                    'pages': 0,
                    'current_page': current_page,
                    'user_group_have_access': '<b><em>Нет данных</em></b>',
                    'post_text': '',
                    'image_url_media': '',
                    'image_visible': False,
                    'button_visible': False,
                }
            # Формируем строку с реакциями
            reactions_str = ", ".join([f"{k}: {v}" for k, v in (post.reactions or {}).items()]) or "Нет данных"
            # Подготавливаем данные для отображения
            published_at = post.published_at.strftime("%Y-%m-%d %H:%M") if post.published_at else ''
            views = post.views or 0
            comments = post.comments or 0
            # Подготавливаем медиа
            image_url_media = ''
            image_visible = False
            if post.image_path:
                image_url_media = MediaAttachment(ContentType.PHOTO, path=post.image_path)
                image_visible = True
            button_visible = len(posts) > 0
            return {
                'pages': pages,
                'current_page': current_page,
                'user_group_have_access': (
                    f"{post.text}\n\n"
                    f"<b>👁️‍🗨️ Просмотры:</b> {views}\n"
                    f"<b>💬 Комментарии:</b> {comments}\n"
                    f"<b>👍 Реакции:</b> {reactions_str}\n"
                    f"<b>📅 Опубликован:</b> {published_at}"
                ),
                'image_url_media': image_url_media,
                'image_visible': image_visible,
                'button_visible': button_visible,
            }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики постов: {e}")
        return {
            'pages': 0,
            'current_page': 0,
            'user_group_have_access': f'Ошибка загрузки статистики: {str(e)}',
            'image_url_media': '',
            'image_visible': False,
            'button_visible': False,
        }


# --- Диалог ---
post_stats_dialog = Dialog(
    Window(
        Format("{user_group_have_access}"),
        DynamicMedia('image_url_media', when='image_visible'),
        StubScroll(id=ID_SCROLL_WITH_PAGER, pages='pages'),
        Row(
            FirstPage(scroll=ID_SCROLL_WITH_PAGER, text=Format("⏮️ {target_page1}")),
            PrevPage(scroll=ID_SCROLL_WITH_PAGER, text=Format("◀️")),
            CurrentPage(scroll=ID_SCROLL_WITH_PAGER, text=Format("{current_page1}")),
            NextPage(scroll=ID_SCROLL_WITH_PAGER, text=Format("▶️")),
            LastPage(scroll=ID_SCROLL_WITH_PAGER, text=Format("{target_page1} ⏭️")),
            when='button_visible'
        ),
        MAIN_MENU_MAIN_BUTTON,
        state=states.StatsStates.STATS_VIEW,
        getter=stats_getter,
        parse_mode='HTML'
    )
)
