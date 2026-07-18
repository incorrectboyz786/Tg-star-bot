"""
REST API routes for the Telegram Mini App web interface.
All routes require Telegram initData verification via Authorization: tma <initData> header.
"""
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional
from aiohttp import web

from database import Database
from utils.helpers import get_rank, streak_bonus, RANKS

logger = logging.getLogger(__name__)

STAR_TIERS = [(15, 1500, "⭐")]
DAILY_BASE = 50


# ── Auth ──────────────────────────────────────────────────────────────────────

def _verify_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    """
    Verify Telegram Web App initData HMAC signature.
    Returns parsed user dict on success, None on failure.
    """
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(computed, received_hash):
            return None

        # Reject stale sessions (1 hour max)
        auth_date = int(parsed.get("auth_date", 0))
        if time.time() - auth_date > 3600:
            return None

        return json.loads(parsed.get("user", "{}"))
    except Exception as e:
        logger.debug("initData verify error: %s", e)
        return None


async def _auth(request: web.Request, db: Database):
    """
    Extract authenticated DB user from request.
    Reads Authorization: tma <initData> header.
    Falls back to DEV_MODE bypass when DEV_MODE=1 env var is set.
    Raises HTTPUnauthorized on failure.
    """
    # Dev bypass for local testing
    if os.environ.get("DEV_MODE") == "1":
        dev_id = int(os.environ.get("DEV_TG_ID", "0"))
        if dev_id:
            user = await db.get_user(dev_id)
            if user:
                return user

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("tma "):
        raise web.HTTPUnauthorized(reason="missing tma token")

    init_data = auth_header[4:]
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    tg_user = _verify_init_data(init_data, bot_token)
    if not tg_user:
        raise web.HTTPUnauthorized(reason="invalid initData")

    user = await db.get_user(tg_user["id"])
    if not user:
        raise web.HTTPUnauthorized(reason="user not registered — open bot first")

    return user


def _json(data) -> web.Response:
    return web.Response(
        text=json.dumps(data, default=str),
        content_type="application/json",
    )


def _err(reason: str, status: int = 400) -> web.Response:
    return web.Response(
        text=json.dumps({"error": reason}),
        content_type="application/json",
        status=status,
    )


# ── Handlers ──────────────────────────────────────────────────────────────────

async def api_me(request: web.Request) -> web.Response:
    """GET /api/me — Full user profile with wallet, streak, rank, referral count."""
    db: Database = request.app["db"]
    try:
        user = await _auth(request, db)
    except web.HTTPException as e:
        return _err(e.reason, e.status_code)

    wallet = await db.get_wallet(user["id"])
    streak_data = await db.get_streak(user["id"])
    rank_emoji, rank_title, rank_next = get_rank(wallet.get("total_earned", 0))
    leaderboard_rank = await db.get_user_leaderboard_rank(user["id"])
    referral_count = await db.get_referral_count(user["id"])
    can_claim = await db.can_claim_daily(user["id"])
    cooldown = await db.get_daily_cooldown(user["id"])

    return _json({
        "id": user["id"],
        "telegram_id": user["telegram_id"],
        "first_name": user["first_name"],
        "username": user["username"],
        "balance": wallet.get("balance", 0),
        "total_earned": wallet.get("total_earned", 0),
        "referral_earnings": wallet.get("referral_earnings", 0),
        "daily_earnings": wallet.get("daily_earnings", 0),
        "streak": streak_data.get("streak", 0),
        "last_claimed": streak_data.get("last_claimed"),
        "rank_emoji": rank_emoji,
        "rank_title": rank_title,
        "rank_next": rank_next,
        "leaderboard_rank": leaderboard_rank,
        "referral_count": referral_count,
        "can_claim_daily": can_claim,
        "daily_cooldown_seconds": int(cooldown.total_seconds()) if cooldown else 0,
        "device_verified": bool(user.get("device_verified")),
        "created_at": user["created_at"],
    })


async def api_daily_status(request: web.Request) -> web.Response:
    """GET /api/daily/status — Daily bonus status and preview amount."""
    db: Database = request.app["db"]
    try:
        user = await _auth(request, db)
    except web.HTTPException as e:
        return _err(e.reason, e.status_code)

    streak_data = await db.get_streak(user["id"])
    streak = streak_data.get("streak", 0)
    can_claim = await db.can_claim_daily(user["id"])
    cooldown = await db.get_daily_cooldown(user["id"])

    next_streak = streak + 1 if can_claim else streak
    preview_amount = streak_bonus(next_streak, DAILY_BASE)

    return _json({
        "can_claim": can_claim,
        "streak": streak,
        "next_streak": next_streak,
        "preview_amount": preview_amount,
        "cooldown_seconds": int(cooldown.total_seconds()) if cooldown else 0,
        "last_claimed": streak_data.get("last_claimed"),
        "streak_milestones": [
            {"days": 3,  "multiplier": "1.2x", "bonus": streak_bonus(3, DAILY_BASE)},
            {"days": 5,  "multiplier": "1.5x", "bonus": streak_bonus(5, DAILY_BASE)},
            {"days": 7,  "multiplier": "2x",   "bonus": streak_bonus(7, DAILY_BASE)},
            {"days": 14, "multiplier": "3x",   "bonus": streak_bonus(14, DAILY_BASE)},
            {"days": 30, "multiplier": "5x",   "bonus": streak_bonus(30, DAILY_BASE)},
        ],
    })


async def api_daily_claim(request: web.Request) -> web.Response:
    """POST /api/daily/claim — Claim today's daily bonus."""
    db: Database = request.app["db"]
    try:
        user = await _auth(request, db)
    except web.HTTPException as e:
        return _err(e.reason, e.status_code)

    if not await db.can_claim_daily(user["id"]):
        cooldown = await db.get_daily_cooldown(user["id"])
        return _err("already_claimed", 409)

    streak_data = await db.get_streak(user["id"])
    old_streak = streak_data.get("streak", 0)
    last_claimed = streak_data.get("last_claimed")

    # Calculate new streak
    if last_claimed:
        try:
            last_dt = datetime.fromisoformat(last_claimed)
            elapsed = datetime.utcnow() - last_dt
            new_streak = (old_streak + 1) if elapsed < timedelta(hours=48) else 1
        except Exception:
            new_streak = 1
    else:
        new_streak = 1

    amount = streak_bonus(new_streak, DAILY_BASE)

    await db.claim_daily_with_streak(user["id"], new_streak)
    await db.add_to_wallet(user["id"], amount, source="daily")

    return _json({
        "claimed": True,
        "amount": amount,
        "streak": new_streak,
        "next_claim_in": 86400,
    })


async def api_referrals(request: web.Request) -> web.Response:
    """GET /api/referrals — Referral stats and referral list."""
    db: Database = request.app["db"]
    try:
        user = await _auth(request, db)
    except web.HTTPException as e:
        return _err(e.reason, e.status_code)

    wallet = await db.get_wallet(user["id"])
    referrals = await db.get_referrals_for_user(user["id"])

    ref_list = []
    for ref in referrals:
        ref_user = await db.get_user_by_id(ref["referee_id"])
        if ref_user:
            ref_list.append({
                "first_name": ref_user.get("first_name", "User"),
                "username": ref_user.get("username"),
                "points_awarded": ref.get("points_awarded", 0),
                "joined_at": ref.get("created_at"),
            })

    bot_username = os.environ.get("BOT_USERNAME", "FREE_ST44R_BOT")
    tg_id = user["telegram_id"]

    return _json({
        "total_referrals": len(referrals),
        "referral_earnings": wallet.get("referral_earnings", 0),
        "referral_link": f"https://t.me/{bot_username}?start={tg_id}",
        "points_per_referral": 100,
        "referrals": ref_list[:50],
    })


async def api_stars_tiers(request: web.Request) -> web.Response:
    """GET /api/stars/tiers — Available star redemption tiers."""
    db: Database = request.app["db"]
    try:
        user = await _auth(request, db)
    except web.HTTPException as e:
        return _err(e.reason, e.status_code)

    wallet = await db.get_wallet(user["id"])
    balance = wallet.get("balance", 0)

    tiers = []
    for stars, cost, icon in STAR_TIERS:
        tiers.append({
            "stars": stars,
            "cost": cost,
            "icon": icon,
            "can_afford": balance >= cost,
            "shortfall": max(0, cost - balance),
        })

    return _json({"balance": balance, "tiers": tiers})


async def api_stars_withdraw(request: web.Request) -> web.Response:
    """POST /api/stars/withdraw — Submit a star withdrawal request."""
    db: Database = request.app["db"]
    try:
        user = await _auth(request, db)
    except web.HTTPException as e:
        return _err(e.reason, e.status_code)

    try:
        body = await request.json()
    except Exception:
        return _err("invalid_json")

    stars = int(body.get("stars", 0))
    valid_tier = next((t for t in STAR_TIERS if t[0] == stars), None)
    if not valid_tier:
        return _err("invalid_tier")

    cost = valid_tier[1]
    wallet = await db.get_wallet(user["id"])
    if wallet.get("balance", 0) < cost:
        return _err("insufficient_balance")

    # Check for pending withdrawal
    pending = await db.get_pending_withdrawals()
    user_pending = [w for w in pending if w["user_id"] == user["id"]]
    if user_pending:
        return _err("pending_withdrawal_exists", 409)

    ok = await db.deduct_from_wallet(user["id"], cost)
    if not ok:
        return _err("deduction_failed")

    w_id = await db.create_withdrawal(user["id"], stars, cost)

    return _json({
        "success": True,
        "withdrawal_id": w_id,
        "stars": stars,
        "cost": cost,
        "message": "Withdrawal request submitted. Admin will process within 24 hours.",
    })


async def api_stars_history(request: web.Request) -> web.Response:
    """GET /api/stars/history — User's withdrawal history."""
    db: Database = request.app["db"]
    try:
        user = await _auth(request, db)
    except web.HTTPException as e:
        return _err(e.reason, e.status_code)

    history = await db.get_user_withdrawals(user["id"])
    return _json({"history": history})


async def api_leaderboard(request: web.Request) -> web.Response:
    """GET /api/leaderboard — Top 50 earners."""
    db: Database = request.app["db"]
    try:
        user = await _auth(request, db)
    except web.HTTPException as e:
        return _err(e.reason, e.status_code)

    import aiosqlite
    async with aiosqlite.connect(db.path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            """SELECT u.first_name, u.username, u.telegram_id,
                      w.total_earned, w.balance
               FROM wallet w
               JOIN users u ON u.id = w.user_id
               WHERE u.is_banned = 0
               ORDER BY w.total_earned DESC
               LIMIT 50"""
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]

    entries = []
    for i, row in enumerate(rows, 1):
        rank_emoji, rank_title, _ = get_rank(row["total_earned"])
        entries.append({
            "position": i,
            "first_name": row["first_name"],
            "username": row["username"],
            "total_earned": row["total_earned"],
            "balance": row["balance"],
            "rank_emoji": rank_emoji,
            "rank_title": rank_title,
            "is_me": row["telegram_id"] == user["telegram_id"],
        })

    my_rank = await db.get_user_leaderboard_rank(user["id"])
    return _json({"entries": entries, "my_rank": my_rank})


# ── CORS middleware ────────────────────────────────────────────────────────────

@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        resp = web.Response()
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return resp
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


# ── Route registration ─────────────────────────────────────────────────────────

def add_api_routes(app: web.Application) -> None:
    app.router.add_get("/api/me", api_me)
    app.router.add_get("/api/daily/status", api_daily_status)
    app.router.add_post("/api/daily/claim", api_daily_claim)
    app.router.add_get("/api/referrals", api_referrals)
    app.router.add_get("/api/stars/tiers", api_stars_tiers)
    app.router.add_post("/api/stars/withdraw", api_stars_withdraw)
    app.router.add_get("/api/stars/history", api_stars_history)
    app.router.add_get("/api/leaderboard", api_leaderboard)
    # OPTIONS preflight for all api routes
    app.router.add_route("OPTIONS", "/api/{path_info:.*}", lambda r: web.Response())
