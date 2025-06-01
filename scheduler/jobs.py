# scheduler/jobs.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from sqlalchemy.future import select
from telegram_api.client import publish_post_to_group
from telegram_api.stats import fetch_post_stats
from config.env import bot_global, conf
from config.logging_config import logger, async_log_exception
from database.models import AsyncSessionLocal, Post

scheduler = AsyncIOScheduler()


@async_log_exception
async def schedule_post_job(scheduled_time: datetime, post_id: int):
    """Добавление задачи в планировщик"""
    async def job():
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Post).where(Post.id == post_id))  # Используем 'id' поста
                post = result.scalars().first()
                if not post:
                    logger.error(f"Пост с ID {post_id} не найден")
                    return
                # Публикация поста
                channel_id = conf.tg_bot.channel_id
                message_id = await publish_post_to_group(channel_id, post.text, post.image_path)
                logger.info(f"Пост {post_id} успешно опубликован по расписанию")
                # Обновление данных в БД
                post.published = True
                post.published_at = datetime.now()
                post.message_id = message_id
                await session.commit()
                # Формирование ссылки
                if channel_id.startswith("-100"):
                    clean_chat_id = channel_id[4:]  # Убираем "-100"
                elif channel_id.startswith("-"):
                    clean_chat_id = channel_id[1:]  # Убираем "-"
                else:
                    clean_chat_id = channel_id
                post_url = f"https://t.me/c/{clean_chat_id}/{message_id}"
                # Отправка уведомления администраторам
                for admin_id in conf.tg_bot.admin_ids:
                    try:
                        await bot_global.send_message(chat_id=admin_id, text=f"<b>⏰ Пост опубликован по расписанию! ✅</b>\n🔗 {post_url}")
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления администратору {admin_id}: {e}")
        except Exception as ee:
            logger.error(f"Ошибка публикации поста {post_id} по расписанию: {ee}")
            # Уведомление администраторов об ошибке
            for admin_id in conf.tg_bot.admin_ids:
                try:
                    await bot_global.send_message(chat_id=admin_id, text=f"❌ Ошибка публикации поста {post_id} по расписанию\n📝 Ошибка: {ee}")
                except Exception as e:
                    logger.exception(f"Не удалось отправить уведомление администратору {admin_id}: {e}")
    # Добавляем задачу в планировщик
    scheduler.add_job(job, 'date', run_date=scheduled_time)


@async_log_exception
async def setup_stats_job():
    """Настройка задачи для регулярного обновления статистики постов"""
    try:
        async def update_stats():
            async with AsyncSessionLocal() as session:
                await fetch_post_stats(session, conf.tg_bot.channel_u)
        # Добавляем задачу для регулярного обновления статистики (каждые 24 часа)
        scheduler.add_job(
            update_stats,
            'interval',
            hours=24,
            id='update_post_stats',
            replace_existing=True
        )
        logger.info("Задача обновления статистики постов добавлена")
    except Exception as e:
        logger.error(f"Ошибка при настройке задачи обновления статистики: {e}")
