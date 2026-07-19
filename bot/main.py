import asyncio
import json
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
from fingerprint_page import get_verify_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def make_web_app(db: Database) -> web.Application:
    """Build the aiohttp web application with health + fingerprint routes."""

    async def health(request: web.Request) -> web.Response:
        return web.Response(text="OK")

    async def verify_page(request: web.Request) -> web.Response:
        token = request.query.get("t", "")
        return web.Response(
            text=get_verify_html(token),
            content_type="text/html",
        )

    async def fingerprint_handler(request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.Response(
                text=json.dumps({"ok": False, "reason": "bad_request"}),
                content_type="application/json",
                status=400,
            )

        token = data.get("token", "")
        fp_hash = data.get("fingerprint", "")

        if not token or not fp_hash:
            return web.Response(
                text=json.dumps({"ok": False, "reason": "missing_fields"}),
                content_type="application/json",
                status=400,
            )

        token_record = await db.get_device_token(token)
        if not token_record or token_record["used"]:
            return web.Response(
                text=json.dumps({"ok": False, "reason": "invalid_token"}),
                content_type="application/json",
            )

        # Check expiry
        from datetime import datetime
        try:
            expires = datetime.strptime(token_record["expires_at"], "%Y-%m-%d %H:%M:%S")
            if datetime.utcnow() > expires:
                return web.Response(
                    text=json.dumps({"ok": False, "reason": "invalid_token"}),
                    content_type="application/json",
                )
        except Exception:
            pass

        user_id = token_record["user_id"]

        # Conflict check — same device, different account?
        conflict = await db.check_fingerprint_conflict(fp_hash, user_id)
        if conflict:
            logger.warning("Device conflict for user_id=%s fp=%s", user_id, fp_hash[:16])
            return web.Response(
                text=json.dumps({"ok": False, "reason": "duplicate_device"}),
                content_type="application/json",
            )

        # All good — store fingerprint and mark verified
        await db.store_fingerprint_and_verify(user_id, fp_hash, token)
        logger.info("Device verified for user_id=%s", user_id)
        return web.Response(
            text=json.dumps({"ok": True}),
            content_type="application/json",
        )

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_get("/verify", verify_page)
    # /fingerprint — direct (dev), /api/fingerprint — Railway single-service
    app.router.add_post("/fingerprint", fingerprint_handler)
    app.router.add_post("/api/fingerprint", fingerprint_handler)
    return app


async def run_web_server(db: Database) -> None:
    # In production PORT=8080; in dev, api-server occupies 8080 so use 8082.
    port = int(os.environ.get("BOT_WEB_PORT", os.environ.get("PORT", 8082)))
    app = make_web_app(db)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    try:
        await site.start()
        logger.info("Web server listening on port %s", port)
    except OSError as e:
        logger.warning("Web server could not start on port %s: %s (skipping)", port, e)


async def web_server_task(db: Database) -> None:
    await run_web_server(db)
    await asyncio.Event().wait()   # stay alive forever


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

    try:
        await asyncio.gather(
            web_server_task(db),
            dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()),
        )
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
