from aiogram import Router, F, Bot
from aiogram.types import Message
from config import SUPPORT_CHANNEL_ID, ADMINS

router = Router()


@router.message(F.chat.id == SUPPORT_CHANNEL_ID, F.reply_to_message)
async def admin_reply_to_user(message: Message, bot: Bot):
    """
    Если админ отвечает reply'ем на сообщение в канале поддержки —
    бот отправляет этот ответ пользователю в ЛС.
    """
    if message.from_user.id not in ADMINS:
        return

    replied = message.reply_to_message

    # Ищем ID пользователя в тексте replied-сообщения или в reply_to_message
    user_id = None

    # Вариант 1: ответ на нашу карточку "🆘 Новое обращение" (в ней есть <code>ID</code>)
    if replied.text and "<code>" in (replied.html_text or ""):
        import re
        m = re.search(r"<code>(\d+)</code>", replied.html_text)
        if m:
            user_id = int(m.group(1))

    # Вариант 2: ответ на пересланное сообщение — Telegram хранит forward_origin
    if user_id is None and replied.forward_origin:
        origin = replied.forward_origin
        # MessageOriginUser
        if hasattr(origin, "sender_user") and origin.sender_user:
            user_id = origin.sender_user.id

    if user_id is None:
        await message.reply("❓ Не удалось определить пользователя.")
        return

    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        await message.reply("✅ Ответ отправлен пользователю.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")