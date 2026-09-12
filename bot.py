import asyncio
import logging

from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from config import BOT_TOKEN, PROXY
from database import init_db
from handlers import user, admin, support_admin

logging.basicConfig(level=logging.INFO)


async def main():
    await init_db()

    # --- Настройка сессии с прокси (если задан) ---
    if PROXY:
        session = AiohttpSession(proxy=PROXY)
        bot = Bot(
            token=BOT_TOKEN,
            session=session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        logging.info(f"Использую прокси: {PROXY}")
    else:
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    # --- Подключение роутеров ---
    dp = Dispatcher()
    dp.include_router(support_admin.router)   # первым
    dp.include_router(admin.router)
    dp.include_router(user.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())