from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def main_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню внизу экрана."""
    kb = ReplyKeyboardBuilder()
    kb.button(text="📝 Отправить сообщение")
    kb.button(text="🆘 Поддержка")
    kb.button(text="ℹ️ О боте")
    kb.adjust(2, 2)
    return kb.as_markup(resize_keyboard=True)


def send_prompt_kb() -> InlineKeyboardMarkup:
    """Кнопка «Отмена» под сообщением с просьбой отправить что-то."""
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data="cancel_action")
    return kb.as_markup()


def support_kb() -> InlineKeyboardMarkup:
    """Кнопки под сообщением поддержки."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✍️ Написать в поддержку", callback_data="support_write")
    kb.button(text="❌ Отмена", callback_data="cancel_action")
    kb.adjust(1)
    return kb.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data="cancel_action")
    return kb.as_markup()