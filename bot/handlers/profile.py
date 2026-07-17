import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database import Database
from utils.helpers import (
    escape_html, format_number, get_rank, rank_progress_bar, progress_bar
)

logger = logging.getLogger(__name__)
router = Router()

ACHIEVEMENT_RULES = [
    (1,   "🤝", "First Referral"),
    (5,   "🌟", "5 Referrals"),
    (10,  "💥", "10 Referrals"),
    (25,  "🚀", "25 Referrals"),
    (50,  "👑", "50 Referrals"),
    (100, "🏆", "100 Referrals"),
]


@router.callback_query(F.data == "profile")
async def cb_profile(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        await cb.answer("Please send /start first.", show_alert=True)
        return

    wallet     = await db.get_wallet(user["id"])
    ref_count  = await db.get_referral_count(user["id"])
    withdrawals = await db.get_user_withdrawals(user["id"])
    leaderboard_rank = await db.get_user_leaderboard_rank(user["id"])

    total_stars    = sum(w["stars_amount"] for w in withdrawals if w["status"] == "approved")
    pending_count  = sum(1 for w in withdrawals if w["status"] == "pending")
    total_earned   = wallet.get("total_earned", 0)
    balance        = wallet.get("balance", 0)

    rank_emoji, rank_title, rank_next = get_rank(total_earned)
    rank_bar  = rank_progress_bar(total_earned, length=12)

    # Achievements
    earned_badges = [
        f"{badge}" for threshold, badge, _ in ACHIEVEMENT_RULES
        if ref_count >= threshold
    ]
    badges_str = "  ".join(earned_badges) if earned_badges else "—"

    # Member since
    created = (user.get("created_at") or "")[:10] or "—"
    username = f"@{user['username']}" if user.get("username") else "—"
    last_name = user.get("last_name") or ""
    full_name = escape_html(f"{user['first_name']} {last_name}".strip())
    verified_icon = "✅" if user.get("device_verified") else "❌"

    # Next rank info
    if rank_next:
        pts_to_next = rank_next - total_earned
        rank_next_str = f"🎯 <b>{format_number(pts_to_next)} pts</b> to next rank"
    else:
        rank_next_str = "🌟 <i>Maximum rank achieved!</i>"

    # Leaderboard position
    lb_str = f"#{leaderboard_rank}" if leaderboard_rank else "—"

    text = (
        f"{'━' * 16}\n"
        f"  {rank_emoji}  <b>{full_name}</b>\n"
        f"  <i>{rank_title}</i>  •  🏅 Rank {lb_str}\n"
        f"{'━' * 16}\n\n"

        f"🔖 <b>Username:</b>     {escape_html(username)}\n"
        f"🆔 <b>Telegram ID:</b>  <code>{tg.id}</code>\n"
        f"📅 <b>Member Since:</b> {created}\n"
        f"🔐 <b>Verified:</b>     {verified_icon}\n\n"

        f"{'─' * 16}\n"
        f"💎 <b>STATS</b>\n"
        f"{'─' * 16}\n"
        f"💰 <b>Balance:</b>       {format_number(balance)} pts\n"
        f"📈 <b>Total Earned:</b>  {format_number(total_earned)} pts\n"
        f"👥 <b>Referrals:</b>     {format_number(ref_count)}\n"
        f"⭐ <b>Stars Earned:</b>  {total_stars} ⭐\n"
        f"⏳ <b>Pending:</b>       {pending_count} request(s)\n\n"

        f"{'─' * 16}\n"
        f"🏆 <b>RANK PROGRESS</b>\n"
        f"{'─' * 16}\n"
        f"{rank_bar}\n"
        f"{rank_next_str}\n\n"

        f"🏅 <b>ACHIEVEMENTS</b>\n"
        f"{badges_str}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⭐ Get Stars", callback_data="get_stars", style="primary"))
    builder.row(InlineKeyboardButton(text="👥 Refer & Earn", callback_data="refer", style="primary"))
    builder.row(InlineKeyboardButton(text="🏠 Back to Menu", callback_data="home", style="primary"))

    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
