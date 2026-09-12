import time
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext

from config import (
    PUBLIC_CHANNEL_ID, LOG_CHANNEL_ID, COOLDOWN,
    REQUIRED_CHANNEL_URL, SUPPORT_CHANNEL_ID, ADMINS
)
from database import (
    upsert_user, get_last_ts, set_last_ts, get_user,
    save_support_map,
)
from keyboards.menus import main_menu_kb, cancel_kb
from states.support import SupportStates
from states.anon import AnonStates
from utils.subscription import is_subscribed

router = Router()


def subscribe_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url=REQUIRED_CHANNEL_URL)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")],
    ])


# =========================================================
# 1. КОМАНДЫ (самый высокий приоритет)
# =========================================================

@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    await upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await message.answer(
        "👋 Привет!\n\n"
        "Я анонимный бот. Отправь мне <b>текст</b>, <b>голосовое</b>, "
        "<b>фото</b>, <b>видео</b> или <b>документ</b> — и я опубликую это "
        "в канале <b>без твоего имени</b>.\n\n"
        f"⏱ Между сообщениями — пауза {COOLDOWN // 60} мин.\n\n"
        "Выбери действие на клавиатуре ниже 👇",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("help"), F.chat.type == ChatType.PRIVATE)
async def help_cmd(message: Message):
    await message.answer(
        "Отправь любое сообщение — оно уйдёт анонимно в канал.\n"
        "Или выбери действие в меню ниже 👇",
        reply_markup=main_menu_kb(),
    )


# =========================================================
# 2. КНОПКИ МЕНЮ (текст кнопок — точное совпадение)
# =========================================================

@router.message(F.text == "ℹ️ О боте")
async def about_cmd(message: Message):
    await message.answer(
        "🤖 <b>Анонимный бот</b>\n\n"
        "• Пересылает твои сообщения в канал анонимно.\n"
        "• Никто из подписчиков канала не узнает, кто ты.\n"
        "🔒 <i>Твой username не публикуется в канале.</i>",
        reply_markup=main_menu_kb(),
    )


@router.message(F.text == "📝 Отправить анонимно")
async def send_prompt(message: Message, state: FSMContext):
    await state.set_state(AnonStates.waiting_anon)
    await message.answer(
        "✍️ Отправь сообщение — оно уйдёт в канал анонимно.\n\n"
        "Можно текст, фото, видео, голосовое или документ.",
        reply_markup=cancel_kb(),
    )


@router.message(F.text == "🆘 Поддержка")
async def support_start(message: Message, state: FSMContext):
    if not SUPPORT_CHANNEL_ID:
        await message.answer("🆘 Поддержка временно недоступна.")
        return
    await state.set_state(SupportStates.waiting_message)
    await message.answer(
        "🆘 <b>Поддержка</b>\n\n"
        "Напиши свой вопрос — администратор ответит тебе прямо здесь, в этом чате.\n\n"
        "Ты можешь отправить текст, фото, видео или голосовое.",
        reply_markup=cancel_kb(),
    )


# =========================================================
# 3. FSM-ХЭНДЛЕРЫ (ловят только в своих состояниях)
# =========================================================

# --- Поддержка ---
@router.message(SupportStates.waiting_message, F.contact)
async def support_contact(message: Message):
    await message.answer("📞 Контакт в поддержку отправлять не нужно.")


@router.message(SupportStates.waiting_message, F.chat.type == ChatType.PRIVATE)
async def support_message(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user = message.from_user

    header = "🆘 <b>Новое обращение</b>\n"
    header += f"👤 {user.full_name}\n"
    if user.username:
        header += f"🔗 @{user.username}\n"
    else:
        header += "🔗 —\n"
    header += f"\n🆔 <code>{user.id}</code>\n"
    header += f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    header += "↩️ <i>Ответьте reply'ем на следующее сообщение, чтобы отправить ответ.</i>"

    sent_any = False
    for admin_id in ADMINS:
        try:
            # 1) Карточка с данными пользователя
            await bot.send_message(admin_id, header)
            # 2) Копия сообщения пользователя
            sent = await bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            # 3) Сохраняем связь "ID сообщения в ЛС админа → user_id"
            await save_support_map(sent.message_id, user.id)
            sent_any = True
        except Exception as e:
            print(f"SUPPORT error for admin {admin_id}:", e)

    if not sent_any:
        await message.answer("❌ Не удалось отправить обращение. Попробуй позже.")
        return

    await message.answer(
        "✅ Обращение отправлено! Администратор скоро ответит.",
        reply_markup=main_menu_kb(),
    )


# --- Анонимная публикация (только по кнопке) ---
@router.message(
    AnonStates.waiting_anon,
    F.chat.type == ChatType.PRIVATE,
    ~F.contact,
)
async def handle_anon(message: Message, state: FSMContext, bot: Bot):
    user = message.from_user

    if not await is_subscribed(bot, user.id):
        await message.answer(
            "🔒 Чтобы отправлять сообщения, подпишись на канал:",
            reply_markup=subscribe_kb(),
        )
        return

    await upsert_user(user.id, user.username, user.full_name)

    last_ts = await get_last_ts(user.id)
    now = int(time.time())
    if now - last_ts < COOLDOWN:
        left = COOLDOWN - (now - last_ts)
        await message.answer(f"⏳ Подожди ещё {left} сек. перед следующим сообщением.")
        return

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
    await state.clear()
    await message.answer(
        "✅ Отправлено анонимно в канал!",
        reply_markup=main_menu_kb(),
    )


# =========================================================
# 4. CALLBACK-КНОПКИ
# =========================================================

@router.callback_query(F.data == "cancel_action")
async def cancel_action(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.edit_text("❌ Действие отменено.")
    except Exception:
        await call.message.answer("❌ Действие отменено.")
    await call.answer()


@router.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery, bot: Bot):
    if await is_subscribed(bot, call.from_user.id):
        await call.message.edit_text(
            "✅ Спасибо за подписку! Теперь можешь отправлять сообщения."
        )
    else:
        await call.answer("❌ Ты ещё не подписался.", show_alert=True)


# =========================================================
# 5. КОНТАКТ (перехватываем, не даём уйти в канал)
# =========================================================

@router.message(F.contact, F.chat.type == ChatType.PRIVATE)
async def contact_handler(message: Message):
    if message.contact.user_id == message.from_user.id:
        await upsert_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            phone=message.contact.phone_number,
        )
    try:
        await message.delete()
    except Exception:
        pass


# =========================================================
# 6. FALLBACK'И (самые низкие приоритеты)
# =========================================================

# Неизвестные команды
@router.message(F.chat.type == ChatType.PRIVATE, F.text.startswith("/"))
async def unknown_command(message: Message):
    await message.answer("❓ Неизвестная команда. Используй /start.")


# Любое сообщение вне FSM-состояний и не команда
@router.message(F.chat.type == ChatType.PRIVATE, ~F.text.startswith("/"), ~F.contact)
async def handle_other(message: Message):
    await message.answer(
        "🤔 Чтобы отправить анонимное сообщение, нажми кнопку "
        "«📝 Отправить анонимно» в меню ниже 👇",
        reply_markup=main_menu_kb(),
    )


# =========================================================
# ХЕЛПЕР
# =========================================================

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