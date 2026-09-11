from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from config import REQUIRED_CHANNEL

# Статусы, означающие "не подписан"
NOT_SUBSCRIBED = {"left", "kicked"}


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """
    Возвращает True, если пользователь подписан на REQUIRED_CHANNEL.
    Бот ОБЯЗАТЕЛЬНО должен быть админом в этом канале.
    """
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status not in NOT_SUBSCRIBED
    except TelegramBadRequest as e:
        # Например, юзер ни разу не заходил в канал
        print("get_chat_member error:", e)
        return False