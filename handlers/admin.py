from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatType

from config import ADMINS
from database import get_all_user_ids, upsert_user

router = Router()

class Broadcast(StatesGroup):
    waiting = State()

# Фильтр "только для админов" в ЛС
def is_admin(message: Message) -> bool:
    return message.chat.type == ChatType.PRIVATE and message.from_user.id in ADMINS

@router.message(Command("admin"), F.chat.type == ChatType.PRIVATE)
async def admin_panel(message: Message):
    if message.from_user.id not in ADMINS:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast")],
    ])
    await message.answer("🛠 Админ-панель", reply_markup=kb)

@router.callback_query(F.data == "broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        await call.answer("Нет доступа", show_alert=True)
        return
    await call.message.answer(
        "Отправь сообщение (текст / фото / видео / голосовое) — "
        "я разошлю его всем пользователям бота от моего лица.\n\n"
        "Для отмены: /cancel"
    )
    await state.set_state(Broadcast.waiting)
    await call.answer()

@router.message(Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    await state.clear()
    await message.answer("❌ Рассылка отменена.")

@router.message(Broadcast.waiting, F.chat.type == ChatType.PRIVATE)
async def do_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in ADMINS:
        return
    await state.clear()

    user_ids = await get_all_user_ids()
    ok, fail = 0, 0
    await message.answer(f"🚀 Начинаю рассылку на {len(user_ids)} пользователей...")

    for uid in user_ids:
        try:
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            ok += 1
        except Exception:
            fail += 1

    await message.answer(f"✅ Готово.\nУспешно: {ok}\nОшибок: {fail}")