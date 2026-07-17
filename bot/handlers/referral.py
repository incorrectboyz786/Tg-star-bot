import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Database
from utils.helpers import format_number, escape_html, truncate, progress_bar

logger = logging.getLogger(__name__)
router = Router()

STAR_TIERS = [
    (15,  300,  "⭐"),
    (50,  900,  "🌟"),
    (100, 1700, "💫"),
    (250, 4000, "🌠"),
]


def _ref_kb(bot_username: str, tg_id: int) -> InlineKeyboardMarkup:
    ref_link = f"https://t.me/{bot_username}?start=ref_{tg_id}"
    share_url = f"https://t.me/share/url?url={ref_link}&text=🌟+Earn+FREE+Telegram+Stars!+Join+now+%26+get+rewarded!"
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📤 Share My Link", url=share_url, style="primary")
    )
    builder.row(
        InlineKeyboardButton(text="📊 My Wallet", callback_data="wallet", style="primary")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Back to Menu", callback_data="home", style="primary")
    )
    return builder.as_markup()


@router.callback_query(F.data == "refer")
async def cb_refer(cb: CallbackQuery, db: Database, bot: Bot) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        await cb.answer("Please send /start first.", show_alert=True)
        return

    bot_info      = await bot.get_me()
    ref_link      = f"https://t.me/{bot_info.username}?start=ref_{tg.id}"
    wallet        = await db.get_wallet(user["id"])
    ref_count     = await db.get_referral_count(user["id"])
    ref_earnings  = wallet.get("referral_earnings", 0)
    balance       = wallet.get("balance", 0)
    reward_per_ref = int(await db.get_setting("referral_reward", "100"))
    lb_rank       = await db.get_user_leaderboard_rank(user["id"])

    # Nearest unlocked/next tier
    next_tier_str = ""
    for stars, cost, icon in STAR_TIERS:
        if balance < cost:
            needed_pts  = cost - balance
            needed_refs = max(1, -(-needed_pts // reward_per_ref))
            bar = progress_bar(balance, cost, length=8)
            next_tier_str = (
                f"{'─' * 16}\n"
                f"{icon} <b>Next Target: {stars} Stars</b>\n"
                f"{bar}\n"
                f"Need <b>{needed_refs} more referral(s)</b>  ({format_number(needed_pts)} pts)\n"
            )
            break
    if not next_tier_str:
        next_tier_str = f"{'─' * 16}\n🎉 <b>You can withdraw any package!</b>\n"

    # Recent referrals
    recent = await db.get_referrals_for_user(user["id"])
    recent_lines = ""
    medals = ["🥇", "🥈", "🥉"] + ["👤"] * 20
    for i, r in enumerate(recent[:5]):
        name = escape_html(truncate(r.get("first_name", "User"), 18))
        recent_lines += f"  {medals[i]} {name}  <b>+{r['points_awarded']} pts</b>\n"

    lb_str = f"#️⃣ <b>Leaderboard Rank:</b>  #{lb_rank}\n\n" if lb_rank else ""

    text = (
        f"{'━' * 16}\n"
        f"  👥  <b>REFER &amp; EARN</b>\n"
        f"{'━' * 16}\n\n"

        f"🔗 <b>Your Referral Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"

        f"{'─' * 16}\n"
        f"📊 <b>YOUR STATS</b>\n"
        f"  👥 Total Referrals:  {format_number(ref_count)}\n"
        f"  💰 Ref Earnings:     {format_number(ref_earnings)} pts\n"
        f"  🎁 Per Referral:     {reward_per_ref} pts\n"
        f"  {lb_str}"

        f"{next_tier_str}\n"
    )

    if recent_lines:
        text += f"{'─' * 16}\n📋 <b>RECENT REFERRALS</b>\n{recent_lines}\n"

    text += (
        f"{'─' * 16}\n"
        f"💡 <b>Tips:</b>\n"
        f"  • Share in groups for more refs!\n"
        f"  • Friends must verify to count\n"
        f"  • No referral limit — earn unlimited!"
    )

    await cb.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=_ref_kb(bot_info.username, tg.id),
    )
