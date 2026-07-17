import aiosqlite
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT NOT NULL,
    last_name TEXT,
    referrer_id INTEGER,
    is_banned INTEGER DEFAULT 0,
    force_join_done INTEGER DEFAULT 0,
    device_verified INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS wallet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    balance INTEGER DEFAULT 0,
    total_earned INTEGER DEFAULT 0,
    referral_earnings INTEGER DEFAULT 0,
    daily_earnings INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referee_id INTEGER UNIQUE NOT NULL,
    points_awarded INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(referrer_id) REFERENCES users(id),
    FOREIGN KEY(referee_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS daily_bonus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    last_claimed TEXT,
    streak INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS device_verification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    device_hash TEXT,
    verified_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS star_withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stars_amount INTEGER NOT NULL,
    points_spent INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now')),
    processed_at TEXT,
    processed_by INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT UNIQUE NOT NULL,
    channel_username TEXT,
    channel_title TEXT,
    invite_link TEXT,
    added_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS broadcast_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT NOT NULL,
    sent_by INTEGER,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    sent_at TEXT DEFAULT (datetime('now'))
);
"""

DEFAULT_SETTINGS = {
    "referral_reward": "100",
    "min_stars_balance": "500",
    "stars_per_claim": "15",
    "daily_bonus_amount": "50",
    "max_referrals": "9999",
    "dm_link": "",
    "welcome_message": "Welcome to TG Stars Bot! Refer friends to earn points and get Telegram Stars! ⭐",
}


class Database:
    def __init__(self, path: str = "bot.db"):
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            for key, value in DEFAULT_SETTINGS.items():
                await db.execute(
                    "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                    (key, value),
                )
            await db.commit()
        logger.info("Database initialised at %s", self.path)

    # ─── Users ────────────────────────────────────────────────────────────────

    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def add_user(
        self,
        telegram_id: int,
        username: Optional[str],
        first_name: str,
        last_name: Optional[str] = None,
        referrer_id: Optional[int] = None,
    ) -> int:
        """Insert user if not exists. Returns internal user id."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT OR IGNORE INTO users
                   (telegram_id, username, first_name, last_name, referrer_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (telegram_id, username, first_name, last_name, referrer_id),
            )
            await db.commit()
            async with db.execute(
                "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cur:
                row = await cur.fetchone()
                user_id = row[0]
            # Ensure wallet row exists
            await db.execute(
                "INSERT OR IGNORE INTO wallet(user_id) VALUES (?)", (user_id,)
            )
            await db.execute(
                "INSERT OR IGNORE INTO daily_bonus(user_id) VALUES (?)", (user_id,)
            )
            await db.commit()
        return user_id

    async def update_user_info(
        self,
        telegram_id: int,
        username: Optional[str],
        first_name: str,
        last_name: Optional[str],
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """UPDATE users SET username=?, first_name=?, last_name=?
                   WHERE telegram_id=?""",
                (username, first_name, last_name, telegram_id),
            )
            await db.commit()

    async def set_force_join_done(self, user_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE users SET force_join_done=1 WHERE id=?", (user_id,)
            )
            await db.commit()

    async def set_device_verified(self, user_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE users SET device_verified=1 WHERE id=?", (user_id,)
            )
            await db.execute(
                """INSERT OR REPLACE INTO device_verification(user_id, verified_at)
                   VALUES (?, datetime('now'))""",
                (user_id,),
            )
            await db.commit()

    async def ban_user(self, telegram_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "UPDATE users SET is_banned=1 WHERE telegram_id=?", (telegram_id,)
            )
            await db.commit()
            return cur.rowcount > 0

    async def unban_user(self, telegram_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "UPDATE users SET is_banned=0 WHERE telegram_id=?", (telegram_id,)
            )
            await db.commit()
            return cur.rowcount > 0

    async def get_all_users(self) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users ORDER BY created_at DESC"
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    # ─── Wallet ───────────────────────────────────────────────────────────────

    async def get_wallet(self, user_id: int) -> Dict:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM wallet WHERE user_id=?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
                if row:
                    return dict(row)
                return {
                    "balance": 0,
                    "total_earned": 0,
                    "referral_earnings": 0,
                    "daily_earnings": 0,
                }

    async def add_to_wallet(
        self,
        user_id: int,
        amount: int,
        earning_type: str = "other",
    ) -> None:
        """earning_type: 'referral' | 'daily' | 'other'"""
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT OR IGNORE INTO wallet(user_id) VALUES (?)", (user_id,))
            if earning_type == "referral":
                await db.execute(
                    """UPDATE wallet SET
                       balance = balance + ?,
                       total_earned = total_earned + ?,
                       referral_earnings = referral_earnings + ?,
                       updated_at = datetime('now')
                       WHERE user_id=?""",
                    (amount, amount, amount, user_id),
                )
            elif earning_type == "daily":
                await db.execute(
                    """UPDATE wallet SET
                       balance = balance + ?,
                       total_earned = total_earned + ?,
                       daily_earnings = daily_earnings + ?,
                       updated_at = datetime('now')
                       WHERE user_id=?""",
                    (amount, amount, amount, user_id),
                )
            else:
                await db.execute(
                    """UPDATE wallet SET
                       balance = balance + ?,
                       total_earned = total_earned + ?,
                       updated_at = datetime('now')
                       WHERE user_id=?""",
                    (amount, amount, user_id),
                )
            await db.commit()

    async def deduct_from_wallet(self, user_id: int, amount: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT balance FROM wallet WHERE user_id=?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
                if not row or row[0] < amount:
                    return False
            await db.execute(
                """UPDATE wallet SET balance = balance - ?,
                   updated_at = datetime('now')
                   WHERE user_id=?""",
                (amount, user_id),
            )
            await db.commit()
            return True

    # ─── Referrals ────────────────────────────────────────────────────────────

    async def add_referral_atomic(
        self, referrer_id: int, referee_id: int, points: int
    ) -> bool:
        """
        Atomically insert a referral row AND credit the referrer's wallet.
        Each referrer can earn from at most max_referrals referrals (default 1).
        Returns True only if the referral was newly inserted and cap not exceeded.
        Uses BEGIN IMMEDIATE to prevent concurrent duplicate awards.
        """
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            try:
                # Fetch referral cap setting (default 1)
                async with db.execute(
                    "SELECT value FROM settings WHERE key='max_referrals'"
                ) as cur:
                    row = await cur.fetchone()
                    max_refs = int(row[0]) if row else 1

                # Check how many referrals referrer already has
                async with db.execute(
                    "SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (referrer_id,)
                ) as cur:
                    count_row = await cur.fetchone()
                    current_count = count_row[0] if count_row else 0

                if current_count >= max_refs:
                    await db.execute("ROLLBACK")
                    return False

                cur = await db.execute(
                    """INSERT OR IGNORE INTO referrals
                       (referrer_id, referee_id, points_awarded) VALUES (?, ?, ?)""",
                    (referrer_id, referee_id, points),
                )
                if cur.rowcount == 0:
                    # Referee already referred by someone — no award
                    await db.execute("ROLLBACK")
                    return False

                # Credit wallet inside the same transaction
                await db.execute("INSERT OR IGNORE INTO wallet(user_id) VALUES (?)", (referrer_id,))
                await db.execute(
                    """UPDATE wallet SET
                       balance = balance + ?,
                       total_earned = total_earned + ?,
                       referral_earnings = referral_earnings + ?,
                       updated_at = datetime('now')
                       WHERE user_id = ?""",
                    (points, points, points, referrer_id),
                )
                await db.execute("COMMIT")
                return True
            except Exception:
                await db.execute("ROLLBACK")
                raise

    async def get_referral_count(self, user_id: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

    async def get_referrals_for_user(self, user_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT r.*, u.first_name, u.username
                   FROM referrals r
                   JOIN users u ON u.id = r.referee_id
                   WHERE r.referrer_id=?
                   ORDER BY r.created_at DESC""",
                (user_id,),
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def referral_exists(self, referee_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT 1 FROM referrals WHERE referee_id=?", (referee_id,)
            ) as cur:
                return (await cur.fetchone()) is not None

    # ─── Daily Bonus ─────────────────────────────────────────────────────────

    async def can_claim_daily(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT last_claimed FROM daily_bonus WHERE user_id=?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
                if not row or not row[0]:
                    return True
                last = datetime.fromisoformat(row[0])
                return datetime.utcnow() - last >= timedelta(hours=24)

    async def get_daily_cooldown(self, user_id: int) -> Optional[timedelta]:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT last_claimed FROM daily_bonus WHERE user_id=?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
                if not row or not row[0]:
                    return None
                last = datetime.fromisoformat(row[0])
                elapsed = datetime.utcnow() - last
                remaining = timedelta(hours=24) - elapsed
                return remaining if remaining.total_seconds() > 0 else None

    async def claim_daily(self, user_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT OR IGNORE INTO daily_bonus(user_id) VALUES (?)""",
                (user_id,),
            )
            await db.execute(
                """UPDATE daily_bonus SET
                   last_claimed = datetime('now'),
                   streak = CASE
                       WHEN last_claimed IS NULL THEN 1
                       WHEN datetime('now') - last_claimed <= '1 day' THEN streak + 1
                       ELSE 1
                   END
                   WHERE user_id=?""",
                (user_id,),
            )
            await db.commit()

    # ─── Reward Codes ─────────────────────────────────────────────────────────

    async def add_reward_code(self, code: str, added_by: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            try:
                await db.execute(
                    "INSERT INTO reward_codes(code, added_by) VALUES (?, ?)",
                    (code, added_by),
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def bulk_add_reward_codes(self, codes: List[str], added_by: int) -> int:
        count = 0
        async with aiosqlite.connect(self.path) as db:
            for code in codes:
                code = code.strip()
                if not code:
                    continue
                try:
                    await db.execute(
                        "INSERT INTO reward_codes(code, added_by) VALUES (?, ?)",
                        (code, added_by),
                    )
                    count += 1
                except aiosqlite.IntegrityError:
                    pass
            await db.commit()
        return count

    async def delete_reward_code(self, code_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "DELETE FROM reward_codes WHERE id=? AND is_used=0", (code_id,)
            )
            await db.commit()
            return cur.rowcount > 0

    async def delete_all_unused_codes(self) -> int:
        """Delete all unused reward codes. Returns number of deleted rows."""
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("DELETE FROM reward_codes WHERE is_used=0")
            await db.commit()
            return cur.rowcount

    async def get_unused_reward_code(self) -> Optional[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM reward_codes WHERE is_used=0 ORDER BY id LIMIT 1"
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def claim_premium_atomic(
        self, user_id: int, min_balance: int
    ) -> dict | None:
        """
        Atomically perform the full Premium claim:
          1. Re-verify balance
          2. Lock and fetch one unused code
          3. Deduct balance
          4. Mark code used, insert assignment, insert claim history
        Returns the code dict on success, or None if any precondition fails.
        Uses BEGIN IMMEDIATE to prevent concurrent double-claims.
        Multiple claims per user are allowed (no one-per-account restriction).
        """
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            try:
                # 1. Check balance
                async with db.execute(
                    "SELECT balance FROM wallet WHERE user_id=?", (user_id,)
                ) as cur:
                    row = await cur.fetchone()
                    if not row or row[0] < min_balance:
                        await db.execute("ROLLBACK")
                        return None

                # 2. Fetch an unused code (locked by IMMEDIATE)
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM reward_codes WHERE is_used=0 ORDER BY id LIMIT 1"
                ) as cur:
                    code_row = await cur.fetchone()
                    if not code_row:
                        await db.execute("ROLLBACK")
                        return None
                    code_dict = dict(code_row)
                db.row_factory = None

                # 4. Deduct balance
                await db.execute(
                    """UPDATE wallet SET balance = balance - ?,
                       updated_at = datetime('now')
                       WHERE user_id = ?""",
                    (min_balance, user_id),
                )

                # 5. Mark code used + assign + history
                await db.execute(
                    "UPDATE reward_codes SET is_used=1 WHERE id=?", (code_dict["id"],)
                )
                await db.execute(
                    "INSERT OR IGNORE INTO assigned_reward_codes(code_id, user_id) VALUES (?, ?)",
                    (code_dict["id"], user_id),
                )
                await db.execute(
                    "INSERT INTO claim_history(user_id, code_id, code) VALUES (?, ?, ?)",
                    (user_id, code_dict["id"], code_dict["code"]),
                )

                await db.execute("COMMIT")
                return code_dict
            except Exception:
                await db.execute("ROLLBACK")
                raise

    async def assign_reward_code(self, code_id: int, user_id: int) -> None:
        """Legacy non-atomic assign — kept for compatibility; prefer claim_premium_atomic."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE reward_codes SET is_used=1 WHERE id=?", (code_id,)
            )
            await db.execute(
                """INSERT INTO assigned_reward_codes(code_id, user_id)
                   VALUES (?, ?)""",
                (code_id, user_id),
            )
            await db.commit()

    async def get_reward_codes(self, used: Optional[bool] = None) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            if used is None:
                async with db.execute(
                    "SELECT * FROM reward_codes ORDER BY id DESC"
                ) as cur:
                    rows = await cur.fetchall()
            else:
                async with db.execute(
                    "SELECT * FROM reward_codes WHERE is_used=? ORDER BY id DESC",
                    (1 if used else 0,),
                ) as cur:
                    rows = await cur.fetchall()
            return [dict(r) for r in rows]

    # ─── Claim History ────────────────────────────────────────────────────────

    async def save_claim(self, user_id: int, code_id: int, code: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO claim_history(user_id, code_id, code)
                   VALUES (?, ?, ?)""",
                (user_id, code_id, code),
            )
            await db.commit()

    async def has_claimed_before(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT 1 FROM claim_history WHERE user_id=? LIMIT 1", (user_id,)
            ) as cur:
                return (await cur.fetchone()) is not None

    async def get_claim_history(self, user_id: Optional[int] = None) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            if user_id:
                async with db.execute(
                    """SELECT ch.*, u.first_name, u.username
                       FROM claim_history ch
                       JOIN users u ON u.id = ch.user_id
                       WHERE ch.user_id=?
                       ORDER BY ch.claimed_at DESC""",
                    (user_id,),
                ) as cur:
                    rows = await cur.fetchall()
            else:
                async with db.execute(
                    """SELECT ch.*, u.first_name, u.username
                       FROM claim_history ch
                       JOIN users u ON u.id = ch.user_id
                       ORDER BY ch.claimed_at DESC LIMIT 50""",
                ) as cur:
                    rows = await cur.fetchall()
            return [dict(r) for r in rows]

    # ─── Channels ────────────────────────────────────────────────────────────

    async def get_channels(self) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM channels ORDER BY id"
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def add_channel(
        self,
        channel_id: str,
        username: Optional[str],
        title: str,
        invite_link: Optional[str] = None,
    ) -> bool:
        async with aiosqlite.connect(self.path) as db:
            try:
                await db.execute(
                    """INSERT INTO channels(channel_id, channel_username, channel_title, invite_link)
                       VALUES (?, ?, ?, ?)""",
                    (channel_id, username, title, invite_link),
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def update_channel_invite_link(
        self, channel_id: str, invite_link: str, title: Optional[str] = None, username: Optional[str] = None
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            if title and username:
                await db.execute(
                    "UPDATE channels SET invite_link=?, channel_title=?, channel_username=? WHERE channel_id=?",
                    (invite_link, title, username, channel_id),
                )
            elif title:
                await db.execute(
                    "UPDATE channels SET invite_link=?, channel_title=? WHERE channel_id=?",
                    (invite_link, title, channel_id),
                )
            else:
                await db.execute(
                    "UPDATE channels SET invite_link=? WHERE channel_id=?",
                    (invite_link, channel_id),
                )
            await db.commit()

    async def remove_channel(self, channel_id: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "DELETE FROM channels WHERE channel_id=?", (channel_id,)
            )
            await db.commit()
            return cur.rowcount > 0

    async def channel_count(self) -> int:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT COUNT(*) FROM channels") as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

    # ─── Settings ────────────────────────────────────────────────────────────

    async def get_setting(self, key: str, default: str = "") -> str:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            ) as cur:
                row = await cur.fetchone()
                return row[0] if row else default

    async def set_setting(self, key: str, value: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)",
                (key, value),
            )
            await db.commit()

    # ─── Streak helpers ───────────────────────────────────────────────────────

    async def get_streak(self, user_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT streak, last_claimed FROM daily_bonus WHERE user_id=?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
                if row:
                    return dict(row)
                return {"streak": 0, "last_claimed": None}

    async def claim_daily_with_streak(self, user_id: int, new_streak: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO daily_bonus(user_id, streak) VALUES (?, 0)", (user_id,)
            )
            await db.execute(
                "UPDATE daily_bonus SET last_claimed=datetime('now'), streak=? WHERE user_id=?",
                (new_streak, user_id),
            )
            await db.commit()

    # ─── Leaderboard rank ─────────────────────────────────────────────────────

    async def get_user_leaderboard_rank(self, user_id: int) -> Optional[int]:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                """SELECT COUNT(*) + 1
                   FROM wallet w
                   JOIN users u ON u.id = w.user_id
                   WHERE u.is_banned = 0
                   AND w.total_earned > (
                       SELECT COALESCE(total_earned, 0) FROM wallet WHERE user_id = ?
                   )""",
                (user_id,),
            ) as cur:
                row = await cur.fetchone()
                return row[0] if row else 1

    # ─── Statistics ───────────────────────────────────────────────────────────

    # ─── Star Withdrawals ─────────────────────────────────────────────────────

    async def create_withdrawal(
        self, user_id: int, stars_amount: int, points_spent: int
    ) -> Optional[int]:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            try:
                async with db.execute(
                    "SELECT balance FROM wallet WHERE user_id=?", (user_id,)
                ) as cur:
                    row = await cur.fetchone()
                    if not row or row[0] < points_spent:
                        await db.execute("ROLLBACK")
                        return None
                await db.execute(
                    "UPDATE wallet SET balance=balance-?, updated_at=datetime('now') WHERE user_id=?",
                    (points_spent, user_id),
                )
                cur = await db.execute(
                    "INSERT INTO star_withdrawals(user_id, stars_amount, points_spent, status) VALUES (?, ?, ?, 'pending')",
                    (user_id, stars_amount, points_spent),
                )
                withdrawal_id = cur.lastrowid
                await db.execute("COMMIT")
                return withdrawal_id
            except Exception:
                await db.execute("ROLLBACK")
                raise

    async def get_withdrawal(self, withdrawal_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT sw.*, u.first_name, u.username, u.telegram_id
                   FROM star_withdrawals sw
                   JOIN users u ON u.id = sw.user_id
                   WHERE sw.id=?""",
                (withdrawal_id,),
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def get_pending_withdrawals(self) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT sw.*, u.first_name, u.username, u.telegram_id
                   FROM star_withdrawals sw
                   JOIN users u ON u.id = sw.user_id
                   WHERE sw.status='pending'
                   ORDER BY sw.created_at ASC""",
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def get_all_withdrawals(self, limit: int = 50) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT sw.*, u.first_name, u.username, u.telegram_id
                   FROM star_withdrawals sw
                   JOIN users u ON u.id = sw.user_id
                   ORDER BY sw.created_at DESC LIMIT ?""",
                (limit,),
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def get_user_withdrawals(self, user_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM star_withdrawals WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
                (user_id,),
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def approve_withdrawal(self, withdrawal_id: int, admin_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "UPDATE star_withdrawals SET status='approved', processed_at=datetime('now'), processed_by=? WHERE id=? AND status='pending'",
                (admin_id, withdrawal_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def reject_withdrawal(self, withdrawal_id: int, admin_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("BEGIN IMMEDIATE")
            try:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM star_withdrawals WHERE id=? AND status='pending'",
                    (withdrawal_id,),
                ) as cur:
                    row = await cur.fetchone()
                    if not row:
                        await db.execute("ROLLBACK")
                        return None
                    w = dict(row)
                db.row_factory = None
                await db.execute(
                    "UPDATE star_withdrawals SET status='rejected', processed_at=datetime('now'), processed_by=? WHERE id=?",
                    (admin_id, withdrawal_id),
                )
                await db.execute(
                    "UPDATE wallet SET balance=balance+?, updated_at=datetime('now') WHERE user_id=?",
                    (w["points_spent"], w["user_id"]),
                )
                await db.execute("COMMIT")
                return w
            except Exception:
                await db.execute("ROLLBACK")
                raise

    # ─── Statistics ───────────────────────────────────────────────────────────

    async def get_stats(self) -> Dict[str, Any]:
        async with aiosqlite.connect(self.path) as db:
            async def scalar(q, *p):
                async with db.execute(q, p) as cur:
                    r = await cur.fetchone()
                    return r[0] if r else 0

            return {
                "total_users": await scalar("SELECT COUNT(*) FROM users"),
                "new_today": await scalar("SELECT COUNT(*) FROM users WHERE date(created_at)=date('now')"),
                "banned_users": await scalar("SELECT COUNT(*) FROM users WHERE is_banned=1"),
                "total_referrals": await scalar("SELECT COUNT(*) FROM referrals"),
                "pending_withdrawals": await scalar("SELECT COUNT(*) FROM star_withdrawals WHERE status='pending'"),
                "approved_withdrawals": await scalar("SELECT COUNT(*) FROM star_withdrawals WHERE status='approved'"),
                "total_stars_sent": await scalar("SELECT COALESCE(SUM(stars_amount),0) FROM star_withdrawals WHERE status='approved'"),
                "total_points": await scalar("SELECT COALESCE(SUM(total_earned),0) FROM wallet"),
            }

    async def get_top_referrers(self, limit: int = 10) -> List[Dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT u.first_name, u.username, u.telegram_id,
                          COUNT(r.id) AS ref_count,
                          COALESCE(w.balance, 0) AS balance
                   FROM users u
                   LEFT JOIN referrals r ON r.referrer_id = u.id
                   LEFT JOIN wallet w ON w.user_id = u.id
                   GROUP BY u.id
                   ORDER BY ref_count DESC
                   LIMIT ?""",
                (limit,),
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def save_broadcast(
        self, message: str, sent_by: int, success: int, fail: int
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO broadcast_history(message, sent_by, success_count, fail_count)
                   VALUES (?, ?, ?, ?)""",
                (message, sent_by, success, fail),
            )
            await db.commit()
