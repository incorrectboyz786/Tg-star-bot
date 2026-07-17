import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from database import Database
from keyboards.user_kb import back_to_menu_kb, confirm_stars_kb
from utils.helpers import format_number

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "get_stars")
async def cb_get_stars(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        await cb.answer("Please send /start first.", show_alert=True)
        return

    min_balance = int(await db.get_setting("min_stars_balance", "500"))
    stars_per_claim = int(await db.get_setting("stars_per_claim", "50"))
    wallet = await db.get_wallet(user["id"])
    balance = wallet.get("balance", 0)

    if balance < min_balance:
        needed = min_balance - balance
        reward_per_ref = int(await db.get_setting("referral_reward", "100"))
        needed_refs = max(1, -(-needed // reward_per_ref))
        text = (
            "❌ <b>Insufficient Points</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⭐ <b>Required:</b> {format_number(min_balance)} pts\n"
            f"💰 <b>Your Balance:</b> {format_number(balance)} pts\n"
            f"📉 <b>Still Need:</b> {format_number(needed)} pts\n\n"
            f"👥 Refer ~{needed_refs} more friend(s) to reach the goal!\n\n"
            "📤 Share your referral link from the <b>Refer &amp; Earn</b> section."
        )
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_menu_kb())
        return

    # Eligible — show confirm screen
    text = (
        "⭐ <b>Withdraw Telegram Stars</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ <b>Your Balance:</b> {format_number(balance)} pts\n"
        f"💸 <b>Points to Spend:</b> {format_number(min_balance)} pts\n"
        f"💰 <b>After Withdrawal:</b> {format_number(balance - min_balance)} pts\n\n"
        f"🌟 <b>You will receive:</b> {stars_per_claim} Telegram Stars ⭐\n\n"
        "ℹ️ Admin will review your request and send Stars directly to your account.\n\n"
        "⚠️ <b>This action cannot be undone.</b> Confirm?"
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=confirm_stars_kb())


@router.callback_query(F.data == "do_withdraw_stars")
async def cb_do_withdraw(cb: CallbackQuery, db: Database, bot: Bot, config) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        return

    min_balance = int(await db.get_setting("min_stars_balance", "500"))
    stars_per_claim = int(await db.get_setting("stars_per_claim", "50"))

    withdrawal_id = await db.create_withdrawal(
        user_id=user["id"],
        stars_amount=stars_per_claim,
        points_spent=min_balance,
    )

    if withdrawal_id is None:
        wallet = await db.get_wallet(user["id"])
        if wallet.get("balance", 0) < min_balance:
            await cb.message.edit_text(
                "❌ <b>Insufficient balance.</b> Earn more points first.",
                parse_mode="HTML",
                reply_markup=back_to_menu_kb(),
            )
        else:
            await cb.message.edit_text(
                "⚠️ <b>Something went wrong.</b> Please try again.",
                parse_mode="HTML",
                reply_markup=back_to_menu_kb(),
            )
        return

    # Notify user
    uname = f"@{tg.username}" if tg.username else f"ID: {tg.id}"
    await cb.message.edit_text(
        f"✅ <b>Withdrawal Request Submitted!</b>\n\n"
        f"🔖 <b>Request ID:</b> #{withdrawal_id}\n"
        f"🌟 <b>Stars:</b> {stars_per_claim} ⭐\n\n"
        f"⏳ Admin will review and send Stars to your account shortly.\n\n"
        f"💡 Track status in <b>My Withdrawals</b>.",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb(),
    )

    # Notify admins
    dm_link = await db.get_setting("dm_link", "")
    admin_text = (
        f"🔔 <b>New Stars Withdrawal Request!</b>\n\n"
        f"🔖 <b>ID:</b> #{withdrawal_id}\n"
        f"👤 <b>User:</b> {tg.first_name} ({uname})\n"
        f"🆔 <b>TG ID:</b> <code>{tg.id}</code>\n"
        f"🌟 <b>Stars:</b> {stars_per_claim} ⭐\n"
        f"💸 <b>Points Spent:</b> {format_number(min_balance)}\n\n"
        f"Use /admin → Pending Withdrawals to approve or reject."
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
            "You haven't made any withdrawal requests yet.\n\n"
            "Earn points and tap ⭐ Get Stars to withdraw!"
        )
    else:
        status_icons = {
            "pending": "⏳",
            "approved": "✅",
            "rejected": "❌",
        }
        lines = []
        for w in withdrawals:
            icon = status_icons.get(w["status"], "❓")
            date = w.get("created_at", "")[:10]
            lines.append(
                f"{icon} #{w['id']} — {w['stars_amount']}⭐ — {w['status'].upper()} ({date})"
            )
        text = (
            "📜 <b>My Withdrawal History</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            + "\n".join(lines)
        )

    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_menu_kb())
