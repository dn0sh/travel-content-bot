# telegram_api/stats.py
import json
import requests
from datetime import datetime
from hydrogram.raw.functions.stats import GetMessageStats
from hydrogram.raw.types import InputChannel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from config.env import bot_global, conf, hydrogram_client
from config.logging_config import logger, async_log_exception, log_exception
from database.models import Post


@log_exception
def parse_timestamp(ts_ms):
    """Преобразует timestamp из миллисекунд в читаемый формат"""
    return datetime.utcfromtimestamp(ts_ms / 1000).strftime('%d.%m.%Y %H:%M')


@log_exception
def process_graph_data(graph_data):
    """Обрабатывает данные графика из JSON"""
    try:
        data = json.loads(graph_data)
        columns = data.get('columns', [])
        x_col = next((col for col in columns if col[0] == 'x'), [])
        y_cols = [col for col in columns if col[0] != 'x']
        if len(x_col) < 2 or not y_cols:
            return []
        result = []
        for i in range(1, len(x_col)):
            time_str = parse_timestamp(x_col[i])
            values = [col[i] for col in y_cols]
            result.append((time_str, values))
        return result
    except Exception as e:
        logger.error(f"602.99 ❌ Ошибка при обработке данных графика: {e}")
        return []


@async_log_exception
async def fetch_post_stats(session: AsyncSession, chat_id: str):
    """Получение статистики по опубликованным постам из Telegram"""
    logger.info(f"Начинаем получение статистики для чата {chat_id}")
    try:
        # Получаем все опубликованные посты
        result = await session.execute(select(Post).where(Post.published == True))
        posts = result.scalars().all()
        async with hydrogram_client:
            # Получаем InputPeerChannel через resolve_peer
            peer = await hydrogram_client.resolve_peer(chat_id)
            # Получаем полную информацию о канале
            channel = await hydrogram_client.get_chat(chat_id)
            # Формируем InputChannel
            input_channel = InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
            for post in posts:
                if not post.message_id:
                    logger.warning(f"603.97 Пост {post.id} не имеет message_id, пропускаем")
                    continue
                try:
                    logger.info(f"603.10 Получаем статистику для поста {post.id} (message_id: {post.message_id})")
                    # Получаем статистику
                    result = await hydrogram_client.invoke(
                        GetMessageStats(
                            channel=input_channel,
                            msg_id=post.message_id,
                            dark=False
                        )
                    )
                    # Обработка графика просмотров
                    if hasattr(result, 'views_graph') and hasattr(result.views_graph, 'json'):
                        graph_data = process_graph_data(result.views_graph.json.data)
                        total_views = sum(sum(values) for _, values in graph_data)
                        post.views = total_views
                        logger.info(f"603.12 Просмотры: {total_views}")
                    # Обработка реакций
                    if hasattr(result, 'reactions_by_emotion_graph') and hasattr(result.reactions_by_emotion_graph, 'json'):
                        graph_data = process_graph_data(result.reactions_by_emotion_graph.json.data)
                        reaction_names = json.loads(result.reactions_by_emotion_graph.json.data).get('names', {})
                        name_map = {key: value for key, value in reaction_names.items() if key.startswith('y')}
                        totals = {}
                        for _, values in graph_data:
                            for i, val in enumerate(values):
                                key = list(name_map.values())[i]
                                totals[key] = totals.get(key, 0) + val
                        post.reactions = totals
                        logger.info(f"603.13 Реакции: {totals}")
                    # Комментарии
                    if hasattr(result, 'comments'):
                        post.comments = result.comments
                        logger.info(f"603.14 Комментарии: {result.comments}")
                    # Сохраняем изменения в БД
                    await session.commit()
                    logger.info(f"603.15 Статистика для поста {post.id} успешно обновлена")
                except Exception as e:
                    logger.error(f"603.98 Ошибка при обработке поста {post.id}: {e}")
                    await session.rollback()
    except Exception as e:
        logger.error(f"603.99 Ошибка при получении статистики: {e}")
        await session.rollback()


@async_log_exception
async def get_post_stats_direct(bot_token: str, chat_id: str, message_id: int):
    # url = f"https://api.telegram.org/bot{bot_token}/getChatMessage"
    # url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    url = f"https://api.telegram.org/bot{bot_token}/getBroadcastStats"
    params = {
        "chat_id": chat_id,
        "message_id": message_id
    }
    response = requests.get(url, params=params).json()
    if response["ok"]:
        message = response["result"]
        return {
            "views": message.get("views", 0),
            "comments": message.get("comment_count", 0)
        }
    else:
        logger.debug(f"Ошибка Telegram API: {response['description']}")
        return {"views": 0, "comments": 0}


@async_log_exception
async def get_channel_stats(bot_token: str, chat_id: str):
    url = f"https://api.telegram.org/bot{bot_token}/getBroadcastStats"
    params = {"chat_id": chat_id}
    response = requests.post(url, json=params)
    return response.json()


@async_log_exception
async def get_post_stats(bot_token: str, chat_id: str, message_id: int):
    url = f"https://api.telegram.org/bot{bot_token}/getPostInteractionCounters"
    params = {
        "channel": chat_id,
        "msg_id": message_id
    }
    response = requests.post(url, json=params)
    return response.json()


@async_log_exception
async def get_message_stats(bot_token: str, chat_id: str, message_id: int):
    url = f"https://api.telegram.org/bot{bot_token}/getMessageStats"
    params = {
        "channel": chat_id,
        "msg_id": message_id
    }
    response = requests.post(url, json=params)
    return response.json()
