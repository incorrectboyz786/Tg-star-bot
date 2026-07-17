import asyncio
import logging
import sys

# Import custom premium emojis to monkeypatch InlineKeyboardButton immediately
import utils.premium_emojis

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.types import ErrorEvent

from config import Config
from database import Database
from middlewares.auth import AuthMiddleware
from handlers import admin, start, profile, referral, wallet, daily_bonus, premium

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    # ── Load config & DB ─────────────────────────────────────────────────────
    config = Config.load()
    db = Database(config.db_path)
    await db.init()

    logger.info("Bot starting. Admin IDs: %s", config.admin_ids)

    # ── Create bot & dispatcher ───────────────────────────────────────────────
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Register premium emoji request middleware
    from utils.premium_emojis import PremiumEmojiRequestMiddleware
    bot.session.middleware.register(PremiumEmojiRequestMiddleware())

    dp = Dispatcher(storage=MemoryStorage())

    # ── Middlewares (must come before routers) ────────────────────────────────
    dp.message.middleware(AuthMiddleware(db, config))
    dp.callback_query.middleware(AuthMiddleware(db, config))

    # ── Register routers — admin first so its FSM has priority ───────────────
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(referral.router)
    dp.include_router(wallet.router)
    dp.include_router(daily_bonus.router)
    dp.include_router(premium.router)

    # ── Print bot info ────────────────────────────────────────────────────────
    bot_info = await bot.get_me()
    logger.info("Bot ready: @%s (id=%s)", bot_info.username, bot_info.id)
    logger.info("Deep link: https://t.me/%s?start=hello", bot_info.username)

    # ── Global error handler ──────────────────────────────────────────────────
    @dp.errors()
    async def global_error_handler(event: ErrorEvent) -> bool:
        err = event.exception
        if isinstance(err, TelegramForbiddenError):
            logger.info("User blocked the bot — ignored: %s", err)
            return True
        if isinstance(err, TelegramBadRequest) and "message is not modified" in str(err):
            return True
        logger.error("Unhandled error: %s", err, exc_info=err)
        return True

    # ── Start polling ─────────────────────────────────────────────────────────
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
