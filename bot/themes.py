# bot/themes.py
from typing import Dict

# Глобальная переменная для хранения тем
global_travel_themes = {}


def set_global_themes(themes: Dict[str, str]):
    """Обновление тем в глобальном хранилище"""
    global global_travel_themes
    global_travel_themes = themes


def get_global_themes() -> Dict[str, str]:
    """Получение текущих тем"""
    return global_travel_themes


def add_theme(theme: str):
    """Добавление новой темы"""
    global global_travel_themes
    if 'themes' not in global_travel_themes:
        global_travel_themes['themes'] = []
    global_travel_themes['themes'].append(theme)


def remove_theme(index: int):
    """Удаление темы по индексу"""
    if 'themes' in global_travel_themes and 0 <= index < len(global_travel_themes['themes']):
        global_travel_themes['themes'].pop(index)