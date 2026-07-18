import asyncio
import logging
import os
import sys
from aiohttp import web

import utils.premium_emojis  # monkeypatches InlineKeyboardButton immediately

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.types import ErrorEvent

from config import Config
from database import Database
from middlewares.auth import AuthMiddleware
from handlers import admin, start, profile, referral, wallet, daily_bonus, stars, help


async def run_health_server() -> None:
    """Minimal HTTP server so Replit deployment health-checks pass."""
    port = int(os.environ.get("PORT", 8080))

    async def health(request: web.Request) -> web.Response:
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    try:
        await site.start()
        logger.info("Health server listening on port %s", port)
    except OSError as e:
        logger.warning("Health server could not start on port %s: %s (skipping)", port, e)


async def health_server_task() -> None:
    """Runs health server and stays alive forever (even if server fails to bind)."""
    await run_health_server()
    # Keep this coroutine alive so gather() doesn't cancel polling
    await asyncio.Event().wait()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    config = Config.load()
    db = Database(config.db_path)
    await db.init()

    logger.info("Bot starting. Admin IDs: %s", config.admin_ids)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    from utils.premium_emojis import PremiumEmojiRequestMiddleware
    bot.session.middleware.register(PremiumEmojiRequestMiddleware())

    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(AuthMiddleware(db, config))
    dp.callback_query.middleware(AuthMiddleware(db, config))

    # Admin router first so its FSM has priority
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(referral.router)
    dp.include_router(wallet.router)
    dp.include_router(daily_bonus.router)
    dp.include_router(stars.router)
    dp.include_router(help.router)

    bot_info = await bot.get_me()
    logger.info("Bot ready: @%s (id=%s)", bot_info.username, bot_info.id)

    @dp.errors()
    async def global_error_handler(event: ErrorEvent) -> bool:
        err = event.exception
        if isinstance(err, TelegramForbiddenError):
            return True
        if isinstance(err, TelegramBadRequest) and "message is not modified" in str(err):
            return True
        logger.error("Unhandled error: %s", err, exc_info=err)
        return True

    # Run health server + bot polling concurrently
    try:
        await asyncio.gather(
            health_server_task(),
            dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()),
        )
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
