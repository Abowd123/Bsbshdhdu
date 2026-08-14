import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.api_client import api_client
from bot.middlewares.auth import AllowedUserMiddleware
from bot.handlers import build_root_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("wolfhost-control-bot")


async def main() -> None:
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    # MemoryStorage عن قصد: لا نريد تخزين محتوى ملفات/أوامر حساسة بشكل دائم على القرص
    dp = Dispatcher(storage=MemoryStorage())

    auth_mw = AllowedUserMiddleware()
    dp.message.outer_middleware(auth_mw)
    dp.callback_query.outer_middleware(auth_mw)

    dp.include_router(build_root_router())

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("WolfHost control bot starting (long polling)…")
    try:
        await dp.start_polling(bot)
    finally:
        await api_client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
