# config/env.py
import pytz
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from dataclasses import dataclass
from datetime import datetime
from environs import Env
from hydrogram import Client
from typing import List, Optional


@dataclass
class TgBot:
    LOG_LEVEL: str
    bot_id_user: str
    bot_token: str
    api_id: str
    api_hash: str
    time_zone: str
    admin_ids: list[int]
    developer_url: str
    channel_id: str
    channel_u: str
    group_chat_id: str

@dataclass
class DbConfig:
    DB_URI: str

@dataclass
class OpenAI:
    api_key: str
    api_url: str
    gpt_model: str
    max_token_count: int

@dataclass
class YandexArt:
    folder_id: str
    gpt_model: str
    gpt_api_url: str
    gpt_api_key: str
    art_model: str
    art_api_url: str
    art_api_key: str

@dataclass
class Config:
    tg_bot: TgBot
    db: DbConfig
    openai: OpenAI
    yandex: YandexArt
    bot_admins: List
    dp: Optional[Dispatcher] = None

def load_config(path: Optional[str] = None) -> Config:
    env: Env = Env()
    env.read_env(path)
    return Config(
        tg_bot=TgBot(
            LOG_LEVEL=str(env('LOG_LEVEL', 'WARNING')),
            bot_id_user=str(env('TELEGRAM_BOT_ID_USER', '')),
            bot_token=str(env('TELEGRAM_BOT_TOKEN', '')),
            api_id=str(env('TELEGRAM_API_ID', '')),
            api_hash=str(env('TELEGRAM_API_HASH', '')),
            time_zone=str(env('TIME_ZONE', 'Europe/Moscow')),
            admin_ids=list(map(int, env.list('TELEGRAM_ADMIN_IDS', default=[]))),
            developer_url=str(env('DEVELOPER_URL', 'https://t.me/turmerig')),
            channel_id=str(env('TELEGRAM_CHANNEL_ID', '')),
            channel_u=str(env('TELEGRAM_CHANNEL_U', '')),
            group_chat_id=str(env('TELEGRAM_GROUP_CHAT_ID', '')),
        ),
        db=DbConfig(
            DB_URI=str(env('DB_URI', 'sqlite+aiosqlite:///./bot.db')),
        ),
        openai=OpenAI(
            api_key=str(env('OPENAI_API_KEY', '')),
            api_url=str(env('OPENAI_API_URL', '')),
            gpt_model=str(env('OPENAI_GPT_MODEL', 'gpt-4o-mini')),
            max_token_count=int(env('OPENAI_MAX_TOKEN_COUNT', 4096))
        ),
        yandex=YandexArt(
            folder_id=str(env('YANDEX_FOLDER_ID', '')),
            gpt_model=str(env('YANDEX_GPT_MODEL', 'yandexgpt/latest')),
            gpt_api_url=str(env('YANDEX_GPT_API_URL', 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion')),
            gpt_api_key=str(env('YANDEX_GPT_API_KEY', '')),
            art_model=str(env('YANDEX_ART_MODEL', 'yandex-art/latest')),
            art_api_url=str(env('YANDEX_ART_API_URL', 'https://llm.api.cloud.yandex.net/foundationModels/v1/imageGenerationAsync')),
            art_api_key=str(env('YANDEX_ART_API_KEY', ''))
        ),
        bot_admins=[],
        dp=None
    )

conf: Config = load_config()
__tz = conf.tg_bot.time_zone if conf.tg_bot.time_zone != '' else 'Europe/Moscow'
bot_timezone = pytz.timezone(__tz)
bot_global = Bot(token=conf.tg_bot.bot_token, default=DefaultBotProperties(parse_mode='HTML'))

# Создаем клиент Hydrogram
hydrogram_client = Client(
    name=conf.tg_bot.bot_id_user,
    api_id=conf.tg_bot.api_id,
    api_hash=conf.tg_bot.api_hash
)

def datetime_local():
    current_time_utc = datetime.now(pytz.utc)
    return current_time_utc.astimezone(bot_timezone).replace(tzinfo=None)
