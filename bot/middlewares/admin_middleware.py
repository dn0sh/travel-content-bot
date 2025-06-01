# bot/middlewares/admin_middleware.py

from aiogram import types
from aiogram import BaseMiddleware
from aiogram.dispatcher.event.bases import CancelHandler

class AdminMiddleware(BaseMiddleware):
    def __init__(self, allowed_admins):
        super().__init__()
        self.allowed_admins = allowed_admins

    async def on_process_message(self, message: types.Message, data: dict):
        if message.from_user.id not in self.allowed_admins:
            await message.answer("У вас нет доступа к этому боту.")
            raise CancelHandler()
