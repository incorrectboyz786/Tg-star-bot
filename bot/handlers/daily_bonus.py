import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database import Database
from utils.helpers import format_number, format_timedelta, streak_bonus, streak_fire, streak_milestone_text

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "daily_bonus")
async def cb_daily_bonus(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        await cb.answer("Please send /start first.", show_alert=True)
        return

    base_bonus  = int(await db.get_setting("daily_bonus_amount", "50"))
    streak_data = await db.get_streak(user["id"])
    streak      = streak_data.get("streak", 0)
    last_claimed = streak_data.get("last_claimed")

    # Check cooldown
    can_claim = True
    remaining = None
    if last_claimed:
        last_dt = datetime.fromisoformat(last_claimed)
        elapsed = datetime.utcnow() - last_dt
        if elapsed < timedelta(hours=24):
            can_claim = False
            remaining = timedelta(hours=24) - elapsed

    if not can_claim:
        time_str = format_timedelta(remaining) if remaining else "soon"
        fire     = streak_fire(streak)
        bonus_preview = streak_bonus(streak + 1, base_bonus)  # next claim amount

        # Build 7-day streak calendar (☑ = claimed, ☐ = not yet)
        calendar = ""
        for d in range(1, 8):
            if d <= min(streak, 7):
                calendar += "✅"
            elif d == min(streak, 7) + 1:
                calendar += "⏳"
            else:
                calendar += "⬜"
        calendar += f"  ({streak} day streak)"

        text = (
            f"🎁 <b>Daily Bonus</b>\n"
            f"{'━' * 16}\n\n"
            f"{fire} <b>Current Streak:</b>  {streak} day(s)\n"
            f"📅 {calendar}\n\n"
            f"⏳ <b>Already claimed!</b>\n"
            f"🕐 <b>Next bonus in:</b>  {time_str}\n\n"
            f"💡 Next claim: <b>+{format_number(bonus_preview)} pts</b>\n\n"
            f"{'─' * 16}\n"
            f"🔥 <b>Streak Multipliers</b>\n"
            f"  ⚡ Day 1-2:   Base pts\n"
            f"  ✨ Day 3-4:   +20%\n"
            f"  ✨ Day 5-6:   +50%\n"
            f"  🔥 Day 7:     ×2\n"
            f"  🔥🔥 Day 14:  ×3\n"
            f"  🔥🔥🔥 Day 30: ×5"
        )
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="👥 Refer & Earn Instead", callback_data="refer", style="primary"))
        builder.row(InlineKeyboardButton(text="🏠 Back to Menu", callback_data="home", style="primary"))
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
        return

    # Determine new streak
    if last_claimed:
        last_dt = datetime.fromisoformat(last_claimed)
        hours_since = (datetime.utcnow() - last_dt).total_seconds() / 3600
        new_streak = streak + 1 if hours_since < 48 else 1
    else:
        new_streak = 1

    bonus_amount = streak_bonus(new_streak, base_bonus)
    milestone    = streak_milestone_text(new_streak)

    # Claim in DB (update streak properly)
    await db.claim_daily_with_streak(user["id"], new_streak)
    await db.add_to_wallet(user["id"], bonus_amount, "daily")
    wallet = await db.get_wallet(user["id"])
    fire   = streak_fire(new_streak)

    # Calendar
    calendar = ""
    for d in range(1, 8):
        if d <= min(new_streak, 7):
            calendar += "✅"
        else:
            calendar += "⬜"
    calendar += f"  ({new_streak} day streak)"

    # Next bonus preview
    next_bonus = streak_bonus(new_streak + 1, base_bonus)

    text = (
        f"🎁 <b>Daily Bonus Claimed!</b>\n"
        f"{'━' * 16}\n\n"
    )
    if milestone:
        text += f"🎉 <b>{milestone}</b>\n\n"

    text += (
        f"{fire} <b>Streak:</b>  {new_streak} day(s)\n"
        f"📅 {calendar}\n\n"
        f"✅ <b>+{format_number(bonus_amount)} pts</b> added!\n"
        f"💰 <b>New Balance:</b>  {format_number(wallet.get('balance', 0))} pts\n\n"
        f"{'─' * 16}\n"
        f"⏰ Come back in <b>24h</b> for your next bonus!\n"
        f"💡 Keep streak → tomorrow: <b>+{format_number(next_bonus)} pts</b>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⭐ Withdraw Stars", callback_data="get_stars", style="primary"))
    builder.row(InlineKeyboardButton(text="👥 Refer & Earn",   callback_data="refer",     style="primary"))
    builder.row(InlineKeyboardButton(text="🏠 Back to Menu",  callback_data="home",      style="primary"))

    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
