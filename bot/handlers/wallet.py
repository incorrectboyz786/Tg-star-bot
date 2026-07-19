import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database import Database
from utils.helpers import format_number, progress_bar, get_rank

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "wallet")
async def cb_wallet(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        await cb.answer("Please send /start first.", show_alert=True)
        return

    w = await db.get_wallet(user["id"])
    balance       = w.get("balance", 0)
    total_earned  = w.get("total_earned", 0)
    ref_earnings  = w.get("referral_earnings", 0)
    daily_earn    = w.get("daily_earnings", 0)

    rank_emoji, rank_title, _ = get_rank(total_earned)

    # Multi-tier progress — load from DB settings
    stars_amt_s = int(await db.get_setting("stars_per_claim", "15"))
    min_bal_s   = int(await db.get_setting("min_stars_balance", "1500"))
    star_tiers  = [(stars_amt_s, min_bal_s, "⭐")]

    tier_lines = ""
    for stars, cost, icon in star_tiers:
        bar = progress_bar(balance, cost, length=8)
        status = "✅ READY" if balance >= cost else f"need {format_number(max(0, cost - balance))}"
        tier_lines += f"  {icon} {stars}⭐ ({format_number(cost)} pts)\n  {bar}  [{status}]\n\n"

    # Earnings breakdown percentages
    total_e = total_earned or 1
    ref_pct   = int(ref_earnings / total_e * 100)
    daily_pct = int(daily_earn   / total_e * 100)
    other_pct = max(0, 100 - ref_pct - daily_pct)

    text = (
        f"{'━' * 16}\n"
        f"  💰  <b>MY WALLET</b>\n"
        f"  {rank_emoji} <i>{rank_title}</i>\n"
        f"{'━' * 16}\n\n"

        f"💎 <b>Current Balance</b>\n"
        f"     <code>{format_number(balance)} pts</code>\n\n"

        f"📊 <b>Earnings Breakdown</b>\n"
        f"  👥 Referrals:  {format_number(ref_earnings)} pts  ({ref_pct}%)\n"
        f"  🎁 Daily:      {format_number(daily_earn)} pts  ({daily_pct}%)\n"
        f"  📈 Total:      {format_number(total_earned)} pts\n\n"

        f"{'─' * 16}\n"
        f"⭐ <b>WITHDRAWAL PROGRESS</b>\n"
        f"{'─' * 16}\n\n"
        f"{tier_lines}"
        f"💡 <i>Refer friends to earn {100} pts each!</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⭐ Withdraw Stars", callback_data="get_stars", style="primary"))
    builder.row(InlineKeyboardButton(text="👥 Refer & Earn",   callback_data="refer",     style="primary"))
    builder.row(InlineKeyboardButton(text="🏠 Back to Menu",  callback_data="home",      style="primary"))

    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
