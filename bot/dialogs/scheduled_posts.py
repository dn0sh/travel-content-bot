# bot/dialogs/scheduled_posts.py
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
async def scheduled_posts_getter(dialog_manager, **kwargs):
    """Возвращает данные о запланированных постах"""
    current_page = await dialog_manager.find(ID_SCROLL_WITH_PAGER).get_page()
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Post)
                .where(Post.scheduled_at.isnot(None), Post.published == False)
                .order_by(Post.scheduled_at.asc())
            )
            posts = result.scalars().all()
            if not posts:
                return {
                    'pages': 0,
                    'current_page': current_page,
                    'user_group_have_access': '<b><em>Нет запланированных постов</em></b>',
                    'post_text': '',
                    'image_url': '',
                    'image_url_media': '',
                    'image_visible': False,
                    'button_visible': False,
                }
            page_size = 1  # 1 пост на страницу
            pages = (len(posts) + page_size - 1) // page_size
            start = current_page * page_size
            end = start + page_size
            post = posts[start:end][0] if start < len(posts) else None
            # if not post:
            #     return {'pages': 0}
            scheduled_at = post.scheduled_at.strftime("%Y-%m-%d %H:%M") if post.scheduled_at else ''
            if post.image_path is not None:
                image_url_media = MediaAttachment(ContentType.PHOTO, path=post.image_path)
                image_visible = True
            else:
                image_url_media = ''
                image_visible = False
            button_visible = False
            if len(posts) > 0:
                button_visible = True
            return {
                'pages': pages,
                'current_page': current_page,
                'user_group_have_access': f"{post.text}\n\n<b>📅 Публикация запланирована ✅ на:</b> {scheduled_at}",
                'post_text': post.text,
                'image_url': post.image_path or '',
                'image_url_media': image_url_media,
                'image_visible': image_visible,
                'button_visible': button_visible,
            }
    except Exception as e:
        logger.error(f"Ошибка при получении запланированных постов: {e}")
        return {
            'pages': 0,
            'current_page': 0,
            'user_group_have_access': f'Ошибка загрузки. {str(e)}',
            'post_text': '',
            'image_url': '',
            'image_url_media': '',
            'image_visible': False,
            'button_visible': False,
        }


async def on_delete_post(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Обработчик нажатия на кнопку 'Удалить пост'"""
    # Получаем данные текущего поста
    current_page = await dialog_manager.find(ID_SCROLL_WITH_PAGER).get_page()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Post)
            .where(Post.scheduled_at.isnot(None), Post.published == False)
            .order_by(Post.scheduled_at.asc())
        )
        posts = result.scalars().all()
        if not posts:
            await callback.answer("Нет постов для удаления")
            return
        page_size = 1
        start = current_page * page_size
        post = posts[start:start + page_size][0] if start < len(posts) else None
        if not post:
            await callback.answer("Пост не найден")
            return
        # Удаляем пост из БД
        await session.delete(post)
        await session.commit()
    # После удаления перезагружаем тот же список
    scroll = dialog_manager.find(ID_SCROLL_WITH_PAGER)
    await scroll.set_page(current_page)
    # Если это была последняя страница и она стала пустой — переходим на предыдущую
    if current_page > 0 and not posts[start + page_size:start + 2 * page_size]:
        await scroll.set_page(current_page - 1)
    await callback.answer("✅ Пост удален", show_alert=False, cache_time=1)


# --- Диалог ---
scheduled_posts_dialog = Dialog(
    Window(
        Format("{user_group_have_access}"),
        # DynamicMedia('image_url_media', when='button_visible'),
        DynamicMedia('image_url_media', when='image_visible'),
        Button(Const("🗑 Удалить пост"), id="btn_delete_post", on_click=on_delete_post, when='button_visible'),
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
        state=states.ScheduledPostsStates.SCHEDULED_POSTS_VIEW,
        getter=scheduled_posts_getter,
        parse_mode='HTML'
    )
)
