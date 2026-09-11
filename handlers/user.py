import time
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatType

from config import (
    PUBLIC_CHANNEL_ID, LOG_CHANNEL_ID, COOLDOWN,
    REQUIRED_CHANNEL_URL,
)
from database import (
    upsert_user, get_last_ts, set_last_ts, get_user,
)
from utils.subscription import is_subscribed

router = Router()

def subscribe_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url=REQUIRED_CHANNEL_URL)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")],
    ])

@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def start_cmd(message: Message):
    await upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await message.answer(
        "👋 Привет!\n\n"
        "Отправь мне текст, голосовое, фото, видео или документ — "
        "я анонимно опубликую это в канале.\n\n"
        f"⏱ Между сообщениями действует задержка {COOLDOWN // 60} мин."
    )


@router.message(Command("help"), F.chat.type == ChatType.PRIVATE)
async def help_cmd(message: Message):
    await message.answer("Отправь любое сообщение — оно уйдёт анонимно в канал.")


# -------- Контакт (номер телефона) — обрабатываем ОТДЕЛЬНО и ПЕРВЫМ --------
# ВАЖНО: этот хэндлер должен быть зарегистрирован ДО handle_any,
# а в handle_any должен стоять фильтр ~F.contact, иначе контакт уйдёт в канал.
@router.message(F.contact, F.chat.type == ChatType.PRIVATE)
async def contact_handler(message: Message):
    if message.contact.user_id == message.from_user.id:
        await upsert_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            phone=message.contact.phone_number,
        )
    # Пользователю НИЧЕГО не отвечаем.
    # Опционально: тихо удалить сообщение с контактом, чтобы не засорять чат:
    try:
        await message.delete()
    except Exception:
        pass


# -------- Приём пользовательских сообщений --------
# ~F.contact — чтобы контакт не попал сюда и не ушёл в канал
@router.message(
    F.chat.type == ChatType.PRIVATE,
    ~F.text.startswith("/"),
    ~F.contact,
)
async def handle_any(message: Message, bot: Bot):
    user = message.from_user
    # --- Проверка подписки на канал ---
    if not await is_subscribed(bot, user.id):
        await message.answer(
            "🔒 Чтобы отправлять сообщения, подпишись на канал:",
            reply_markup=subscribe_kb(),
        )
        return
    await upsert_user(user.id, user.username, user.full_name)

    # Проверка КД
    last_ts = await get_last_ts(user.id)
    now = int(time.time())
    if now - last_ts < COOLDOWN:
        left = COOLDOWN - (now - last_ts)
        await message.answer(f"⏳ Подожди ещё {left} сек. перед следующим сообщением.")
        return

    # Публикация в канал
    try:
        await bot.copy_message(
            chat_id=PUBLIC_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
    except Exception as e:
        await message.answer("❌ Не удалось отправить сообщение в канал.")
        print("PUBLIC_CHANNEL error:", e)
        return

    # Лог в закрытый канал
    info = await _build_user_info(user.id)
    try:
        await bot.send_message(LOG_CHANNEL_ID, info)
        await bot.copy_message(
            chat_id=LOG_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
    except Exception as e:
        print("LOG_CHANNEL error:", e)

    await set_last_ts(user.id, now)
    await message.answer("✅ Отправлено анонимно в канал!")


async def _build_user_info(user_id: int) -> str:
    row = await get_user(user_id)
    if not row:
        return f"👤 ID: <code>{user_id}</code>"
    _, username, full_name, phone = row
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "🆕 <b>Новое сообщение</b>",
        f"👤 Имя: {full_name}",
        f"🔗 Username: @{username}" if username else "🔗 Username: —",
        f"📞 Телефон: {phone}" if phone else "📞 Телефон: —",
        f"🆔 ID: <code>{user_id}</code>",
        f"🕒 {ts}",
    ]
    return "\n".join(lines)
@router.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery, bot: Bot):
    if await is_subscribed(bot, call.from_user.id):
        await call.message.edit_text(
            "✅ Спасибо за подписку! Теперь можешь отправлять сообщения."
        )
    else:
        await call.answer("❌ Ты ещё не подписался.", show_alert=True)