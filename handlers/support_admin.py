from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.enums import ChatType

from config import ADMINS
from database import get_support_user

router = Router()


@router.message(
    F.chat.type == ChatType.PRIVATE,
    F.from_user.id.in_(ADMINS),
    F.reply_to_message,
)
async def admin_reply_to_user(message: Message, bot: Bot):
    """
    Админ отвечает reply'ем на сообщение в ЛС бота —
    бот пересылает ответ пользователю с пометкой.
    """
    replied = message.reply_to_message

    # 1) Прямой reply на сообщение пользователя
    user_id = await get_support_user(replied.message_id)

    # 2) Фолбэк: reply на карточку
    if user_id is None and replied.reply_to_message:
        user_id = await get_support_user(replied.reply_to_message.message_id)

    if user_id is None:
        await message.reply("❓ Не удалось определить пользователя.")
        return

    try:
        # Если это чистый текст (без форматирования и без медиа) —
        # отправляем одним сообщением с заголовком
        if message.text and not message.entities:
            await bot.send_message(
                user_id,
                f"✅ <b>Администратор ответил на ваш вопрос:</b>\n\n{message.text}",
            )
        else:
            # Всё остальное (фото, видео, голос, документ, текст с форматированием) —
            # заголовок отдельно, потом копия сообщения
            await bot.send_message(
                user_id,
                "✅ <b>Администратор ответил на ваш вопрос:</b>",
            )
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )

        await message.reply("✅ Ответ отправлен пользователю.")
    except Exception as e:
        print(f"REPLY error to user {user_id}:", e)
        await message.reply(f"❌ Ошибка: {e}")