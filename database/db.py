# database/db.py
from sqlalchemy.future import select
from database.models import AsyncSessionLocal, GenerationType, Post
from config.logging_config import async_log_exception


@async_log_exception
async def save_post_to_db(dialog_data: dict):
    async with AsyncSessionLocal() as session:
        # Извлечение ID поста
        post_id = dialog_data.get("post_id")
        if post_id is not None:
            # Загружаем существующий пост
            result = await session.execute(select(Post).where(Post.id == post_id))
            post = result.scalars().first()
            if not post:
                # Если пост не найден, создаём новый
                post = Post()
        else:
            post = Post()
        # Обновляем поля поста из dialog_data
        post.text_prompt = dialog_data.get("text_prompt")
        post.text = dialog_data.get("post_text")
        post.model_text = dialog_data.get("model_text")
        post.generated_at_text = dialog_data.get("generated_at_text")
        post.status_text = dialog_data.get("status_text", GenerationType.SUCCESS)
        post.image_prompt = dialog_data.get("image_prompt")
        post.image_path = dialog_data.get("image_url")
        post.model_image = dialog_data.get("model_image")
        post.generated_at_image = dialog_data.get("generated_at_image")
        post.is_scheduled = dialog_data.get("is_scheduled", False)
        post.scheduled_at = dialog_data.get("scheduled_at")
        post.published = dialog_data.get("published", False)
        post.published_at = dialog_data.get("published_at")
        post.status_image = dialog_data.get("status_image", GenerationType.SUCCESS)
        post.error_message = dialog_data.get("error_message")
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post
	

@async_log_exception
async def save_post_to_db_directly(dialog_data: dict):
    """
    Сохранение поста напрямую, без DialogManager
    """
    async with AsyncSessionLocal() as session:
        post = Post(
            text=dialog_data.get("post_text"),
            text_prompt=dialog_data.get("text_prompt"),
            model_text=dialog_data.get("model_text"),
            image_path=dialog_data.get("image_url"),
            image_prompt=dialog_data.get("image_prompt"),
            model_image=dialog_data.get("model_image"),
            error_message=dialog_data.get("error_message"),
            is_scheduled=dialog_data.get("is_scheduled", False),
            scheduled_at=dialog_data.get("scheduled_at"),
            status_text=dialog_data.get("status_text", GenerationType.SUCCESS.value),  # Установка статуса текста
            status_image=dialog_data.get("status_image", GenerationType.SUCCESS.value),  # Установка статуса изображения
        )
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post

		
@async_log_exception
async def get_posts_by_status(status: GenerationType):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Post).where(Post.status_text == status))
        return result.scalars().all()
