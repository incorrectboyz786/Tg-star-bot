import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import Database
from keyboards.user_kb import back_to_menu_kb
from utils.helpers import format_number

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
    min_balance = int(await db.get_setting("min_stars_balance", "500"))
    stars_per_claim = int(await db.get_setting("stars_per_claim", "50"))
    balance = w.get("balance", 0)
    needed = max(0, min_balance - balance)
    progress_pct = min(100, int(balance / min_balance * 100)) if min_balance else 100

    filled = progress_pct // 10
    bar = "█" * filled + "░" * (10 - filled)

    text = (
        "💰 <b>Your Wallet</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 <b>Current Balance:</b>   {format_number(balance)} pts\n"
        f"📈 <b>Total Earned:</b>      {format_number(w.get('total_earned', 0))} pts\n"
        f"👥 <b>Referral Earnings:</b> {format_number(w.get('referral_earnings', 0))} pts\n"
        f"🎁 <b>Daily Earnings:</b>    {format_number(w.get('daily_earnings', 0))} pts\n\n"
        f"🌟 <b>Withdrawal Rate:</b> {format_number(min_balance)} pts = {stars_per_claim} Stars ⭐\n\n"
        f"📊 <b>Progress to Next Withdrawal:</b>\n"
        f"{bar}  {progress_pct}%\n\n"
    )
    if needed > 0:
        text += f"⚡ <b>Need {format_number(needed)} more points</b> — keep referring!"
    else:
        text += "🎉 <b>You have enough points!</b> Tap ⭐ Get Stars to withdraw."

    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_menu_kb())
