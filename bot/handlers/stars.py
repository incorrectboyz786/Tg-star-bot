import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database import Database
from keyboards.user_kb import back_to_menu_kb, stars_tiers_kb, confirm_tier_kb
from utils.helpers import format_number

logger = logging.getLogger(__name__)
router = Router()

# ── Star tiers: (stars, points_cost) ─────────────────────────────────────────
STAR_TIERS = [
    (15, 1500, "⭐"),
]


@router.callback_query(F.data == "get_stars")
async def cb_get_stars(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        await cb.answer("Please send /start first.", show_alert=True)
        return

    wallet = await db.get_wallet(user["id"])
    balance = wallet.get("balance", 0)
    reward_per_ref = int(await db.get_setting("referral_reward", "100"))

    # Load tiers from DB settings
    stars_amt = int(await db.get_setting("stars_per_claim", "15"))
    min_bal   = int(await db.get_setting("min_stars_balance", "1500"))
    star_tiers = [(stars_amt, min_bal, "⭐")]

    # Progress bar toward first tier
    first_cost = star_tiers[0][1]
    pct = min(100, int(balance / first_cost * 100)) if first_cost else 100
    filled = pct // 10
    bar = "█" * filled + "░" * (10 - filled)

    # Build tier lines
    tier_lines = ""
    for stars, cost, icon in star_tiers:
        if balance >= cost:
            tier_lines += f"  {icon} <b>{stars} Stars</b> — {format_number(cost)} pts ✅\n"
        else:
            need = cost - balance
            tier_lines += f"  {icon} <b>{stars} Stars</b> — {format_number(cost)} pts 🔒 (need {format_number(need)} more)\n"

    text = (
        "⭐ <b>Telegram Stars Withdrawal</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Your Balance:</b>  <code>{format_number(balance)} pts</code>\n"
        f"📊 <b>Progress:</b>  {bar}  {pct}%\n\n"
        "🎯 <b>Choose Your Stars Package:</b>\n\n"
        f"{tier_lines}\n"
        "💡 <i>Tap an unlocked package to withdraw!</i>"
    )
    await cb.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=stars_tiers_kb(balance, star_tiers),
    )


@router.callback_query(F.data.startswith("stars_tier_"))
async def cb_select_tier(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        return

    stars_amt_setting = int(await db.get_setting("stars_per_claim", "15"))
    min_bal_setting   = int(await db.get_setting("min_stars_balance", "1500"))
    star_tiers = [(stars_amt_setting, min_bal_setting, "⭐")]

    stars = int(cb.data.split("_")[2])
    tier = next(((s, c, i) for s, c, i in star_tiers if s == stars), None)
    if not tier:
        return

    stars_amt, cost, icon = tier
    wallet = await db.get_wallet(user["id"])
    balance = wallet.get("balance", 0)

    if balance < cost:
        await cb.answer(f"❌ Need {format_number(cost - balance)} more points!", show_alert=True)
        return

    text = (
        f"{icon} <b>Confirm Withdrawal</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⭐ <b>Stars You'll Get:</b>     <code>{stars_amt} Stars</code>\n"
        f"💸 <b>Points to Spend:</b>    <code>{format_number(cost)} pts</code>\n"
        f"💰 <b>Balance After:</b>       <code>{format_number(balance - cost)} pts</code>\n\n"
        "╔══════════════════════════╗\n"
        f"║  🌟  <b>{stars_amt} Telegram Stars</b>  🌟  ║\n"
        "╚══════════════════════════╝\n\n"
        "📬 Admin will send Stars directly to your account.\n"
        "⚠️ <b>This cannot be undone. Confirm?</b>"
    )
    await cb.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=confirm_tier_kb(stars_amt, cost),
    )


@router.callback_query(F.data.startswith("do_withdraw_"))
async def cb_do_withdraw(cb: CallbackQuery, db: Database, bot: Bot, config) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        return

    try:
        parts = cb.data.split("_")   # do_withdraw_{stars}_{cost}
        stars_amt = int(parts[2])
        cost = int(parts[3])
    except (IndexError, ValueError):
        await cb.message.edit_text("⚠️ <b>Invalid request.</b> Please try again.", parse_mode="HTML", reply_markup=back_to_menu_kb())
        return

    withdrawal_id = await db.create_withdrawal(
        user_id=user["id"],
        stars_amount=stars_amt,
        points_spent=cost,
    )

    if withdrawal_id is None:
        wallet = await db.get_wallet(user["id"])
        msg = (
            "❌ <b>Insufficient balance.</b> Earn more points first."
            if wallet.get("balance", 0) < cost
            else "⚠️ <b>Something went wrong.</b> Please try again."
        )
        await cb.message.edit_text(msg, parse_mode="HTML", reply_markup=back_to_menu_kb())
        return

    uname = f"@{tg.username}" if tg.username else f"ID:{tg.id}"
    await cb.message.edit_text(
        "✅ <b>Withdrawal Request Submitted!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔖 <b>Request ID:</b>  <code>#{withdrawal_id}</code>\n"
        f"⭐ <b>Stars:</b>         <code>{stars_amt} ⭐</code>\n"
        f"💸 <b>Points Spent:</b>  <code>{format_number(cost)} pts</code>\n\n"
        "⏳ <i>Admin will review and send Stars shortly.</i>\n\n"
        "📜 Track your request in <b>My Withdrawals</b>.",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb(),
    )

    # Notify admins
    admin_text = (
        f"🔔 <b>New Stars Withdrawal!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔖 <b>ID:</b> #{withdrawal_id}\n"
        f"👤 <b>User:</b> {tg.first_name} ({uname})\n"
        f"🆔 <b>TG ID:</b> <code>{tg.id}</code>\n"
        f"⭐ <b>Stars:</b> {stars_amt} ⭐\n"
        f"💸 <b>Points:</b> {format_number(cost)}\n\n"
        f"➡️ /admin → Pending Withdrawals"
    )
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="HTML")
        except Exception:
            pass


@router.callback_query(F.data == "my_withdrawals")
async def cb_my_withdrawals(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        await cb.answer("Please send /start first.", show_alert=True)
        return

    withdrawals = await db.get_user_withdrawals(user["id"])

    if not withdrawals:
        text = (
            "📜 <b>My Withdrawals</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🌙 <i>No withdrawal requests yet.</i>\n\n"
            "Earn points and tap <b>⭐ Get Stars</b> to start!"
        )
    else:
        status_icons = {"pending": "⏳", "approved": "✅", "rejected": "❌"}
        total_approved = sum(w["stars_amount"] for w in withdrawals if w["status"] == "approved")
        lines = []
        for w in withdrawals:
            icon = status_icons.get(w["status"], "❓")
            date = str(w.get("created_at", ""))[:10]
            lines.append(
                f"{icon} <code>#{w['id']}</code> — <b>{w['stars_amount']}⭐</b> — {w['status'].upper()} <i>({date})</i>"
            )
        text = (
            "📜 <b>My Withdrawal History</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            + "\n".join(lines)
            + f"\n\n🌟 <b>Total Stars Earned:</b> {total_approved} ⭐"
        )

    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_menu_kb())
