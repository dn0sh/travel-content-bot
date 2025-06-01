# bot/dialogs/common.py
from aiogram_dialog import StartMode
from aiogram_dialog.widgets.kbd import Start
from aiogram_dialog.widgets.text import Const
from . import states

MAIN_MENU_MAIN_BUTTON = Start(text=Const('✳️ МЕНЮ'), id='__main__', state=states.PostStates.MAIN, mode=StartMode.RESET_STACK)
