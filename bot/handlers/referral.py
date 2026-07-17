import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Database
from keyboards.user_kb import back_to_menu_kb
from utils.helpers import format_number, escape_html, truncate

logger = logging.getLogger(__name__)
router = Router()


def _referral_share_kb(bot_username: str, tg_id: int) -> InlineKeyboardMarkup:
    ref_link = f"https://t.me/{bot_username}?start=ref_{tg_id}"
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📤 Share My Link",
            url=f"https://t.me/share/url?url={ref_link}&text=Join+and+earn+Telegram+Stars+for+free!",
        )
    )
    builder.row(InlineKeyboardButton(text="🏠 Back to Menu", callback_data="home"))
    return builder.as_markup()


@router.callback_query(F.data == "refer")
async def cb_refer(cb: CallbackQuery, db: Database, bot: Bot) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        await cb.answer("Please send /start first.", show_alert=True)
        return

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{tg.id}"
    wallet = await db.get_wallet(user["id"])
    ref_count = await db.get_referral_count(user["id"])
    reward_per_ref = await db.get_setting("referral_reward", "100")
    min_balance = await db.get_setting("min_stars_balance", "500")
    stars_per_claim = await db.get_setting("stars_per_claim", "50")
    refs_needed = max(0, (int(min_balance) - wallet.get("balance", 0)))
    refs_to_stars = max(0, -(-refs_needed // int(reward_per_ref)))

    recent = await db.get_referrals_for_user(user["id"])
    recent_lines = ""
    for i, r in enumerate(recent[:5], 1):
        name = escape_html(truncate(r.get("first_name", "User"), 20))
        recent_lines += f"   {i}. {name} (+{r['points_awarded']} pts)\n"

    text = (
        "👥 <b>Refer &amp; Earn</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 <b>Your Referral Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"💰 <b>Reward per referral:</b> {reward_per_ref} pts\n"
        f"👥 <b>Total referrals:</b> {format_number(ref_count)}\n"
        f"💎 <b>Referral earnings:</b> {format_number(wallet.get('referral_earnings', 0))} pts\n\n"
        f"⭐ <b>To withdraw {stars_per_claim} Stars:</b> {min_balance} pts needed\n"
        f"📊 <b>You need ~{refs_to_stars} more referral(s)</b>\n\n"
    )
    if recent_lines:
        text += f"📋 <b>Recent Referrals:</b>\n{recent_lines}\n"
    text += "📤 Share your link with friends to earn more!"

    await cb.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=_referral_share_kb(bot_info.username, tg.id),
    )
