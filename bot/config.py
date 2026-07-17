import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

_BOT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DB = os.path.join(_BOT_DIR, "bot.db")

load_dotenv(os.path.join(_BOT_DIR, ".env"))


@dataclass
class Config:
    bot_token: str
    admin_ids: List[int]
    db_path: str = _DEFAULT_DB

    @classmethod
    def load(cls) -> "Config":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")

        raw = os.getenv("ADMIN_IDS", "")
        admin_ids: List[int] = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                admin_ids.append(int(part))

        if not admin_ids:
            raise ValueError("ADMIN_IDS environment variable is not set or invalid.")

        return cls(bot_token=token, admin_ids=admin_ids)
