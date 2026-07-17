from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from database import Database
from config import Config


class AuthMiddleware(BaseMiddleware):
    def __init__(self, db: Database, config: Config) -> None:
        self.db = db
        self.config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["db"] = self.db
        data["config"] = self.config

        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
            if user:
                db_user = await self.db.get_user(user.id)
                if db_user and db_user.get("is_banned"):
                    if isinstance(event, CallbackQuery):
                        await event.answer("🚫 You are banned from this bot.", show_alert=True)
                    else:
                        await event.answer("🚫 You are banned from this bot.")
                    return

        return await handler(event, data)
