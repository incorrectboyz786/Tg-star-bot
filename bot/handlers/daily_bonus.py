import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import Database
from keyboards.user_kb import back_to_menu_kb
from utils.helpers import format_number, format_timedelta

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

    can_claim = await db.can_claim_daily(user["id"])

    if not can_claim:
        remaining = await db.get_daily_cooldown(user["id"])
        time_str = format_timedelta(remaining) if remaining else "soon"
        text = (
            "🎁 <b>Daily Bonus</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏳ <b>Already claimed today!</b>\n\n"
            f"🕐 <b>Next bonus in:</b> {time_str}\n\n"
            "Come back tomorrow for more free points! 💰"
        )
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_menu_kb())
        return

    bonus_amount = int(await db.get_setting("daily_bonus_amount", "50"))
    await db.claim_daily(user["id"])
    await db.add_to_wallet(user["id"], bonus_amount, "daily")
    wallet = await db.get_wallet(user["id"])

    text = (
        "🎁 <b>Daily Bonus Claimed!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ <b>+{format_number(bonus_amount)} points</b> added!\n\n"
        f"💰 <b>New Balance:</b> {format_number(wallet.get('balance', 0))} pts\n\n"
        "⏰ Come back in 24 hours for your next bonus!\n\n"
        "💡 <i>Tip: Refer friends to earn even more points!</i>"
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_menu_kb())
