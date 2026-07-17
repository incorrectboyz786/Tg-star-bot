import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import Database
from keyboards.user_kb import back_to_menu_kb
from utils.helpers import escape_html, format_number

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "profile")
async def cb_profile(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        await cb.answer("Please send /start first.", show_alert=True)
        return

    wallet = await db.get_wallet(user["id"])
    ref_count = await db.get_referral_count(user["id"])
    withdrawals = await db.get_user_withdrawals(user["id"])
    total_stars = sum(w["stars_amount"] for w in withdrawals if w["status"] == "approved")
    pending_count = sum(1 for w in withdrawals if w["status"] == "pending")

    username = f"@{user['username']}" if user.get("username") else "—"
    last_name = user.get("last_name") or ""
    full_name = f"{user['first_name']} {last_name}".strip()
    created = (user.get("created_at") or "")[:10] or "—"

    min_balance = int(await db.get_setting("min_stars_balance", "500"))
    stars_ready = wallet.get("balance", 0) >= min_balance
    verified_icon = "✅" if user.get("device_verified") else "❌"

    text = (
        "👤 <b>Your Profile</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 <b>Name:</b> {escape_html(full_name)}\n"
        f"🔖 <b>Username:</b> {escape_html(username)}\n"
        f"🆔 <b>Telegram ID:</b> <code>{tg.id}</code>\n"
        f"📅 <b>Member Since:</b> {created}\n\n"
        f"💰 <b>Balance:</b> {format_number(wallet.get('balance', 0))} pts\n"
        f"📈 <b>Total Earned:</b> {format_number(wallet.get('total_earned', 0))} pts\n"
        f"👥 <b>Total Referrals:</b> {format_number(ref_count)}\n\n"
        f"⭐ <b>Stars Received:</b> {total_stars} ⭐\n"
        f"⏳ <b>Pending Requests:</b> {pending_count}\n\n"
        f"🔐 <b>Verified:</b> {verified_icon}\n"
        f"{'⭐ Ready to withdraw Stars!' if stars_ready else '📊 Keep earning points!'}"
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_menu_kb())
