import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from database import Database
from keyboards.user_kb import back_to_menu_kb, claim_premium_kb, confirm_claim_kb
from utils.helpers import format_number

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "get_premium")
async def cb_get_premium(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        await cb.answer("Please send /start first.", show_alert=True)
        return

    min_balance = int(await db.get_setting("min_premium_balance", "500"))
    wallet = await db.get_wallet(user["id"])
    balance = wallet.get("balance", 0)
    unused_code = await db.get_unused_reward_code()

    # ── No codes available ─────────────────────────────────────────────────
    if not unused_code:
        await cb.message.edit_text(
            "😔 <b>No Reward Codes Available</b>\n\n"
            "All reward codes have been claimed for now.\n"
            "Please check back later or contact the admin.\n\n"
            "Keep earning points in the meantime! 💪",
            parse_mode="HTML",
            reply_markup=back_to_menu_kb(),
        )
        return

    # ── Insufficient balance ───────────────────────────────────────────────
    if balance < min_balance:
        needed = min_balance - balance
        needed_refs = max(1, -(-needed // int(await db.get_setting("referral_reward", "100"))))
        text = (
            "❌ <b>Insufficient Points</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⭐ <b>Required:</b> {format_number(min_balance)} pts\n"
            f"💰 <b>Your Balance:</b> {format_number(balance)} pts\n"
            f"📉 <b>Still Need:</b> {format_number(needed)} pts\n\n"
            f"👥 Refer ~{needed_refs} more friend(s) to reach the goal!\n\n"
            "📤 Share your referral link from the <b>Refer &amp; Earn</b> section."
        )
        await cb.message.edit_text(
            text, parse_mode="HTML", reply_markup=back_to_menu_kb()
        )
        return

    # ── Eligible — show confirm screen ─────────────────────────────────────
    text = (
        "⭐ <b>Claim Telegram Premium</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ <b>Your Balance:</b> {format_number(balance)} pts\n"
        f"💎 <b>Cost:</b> {format_number(min_balance)} pts\n"
        f"💰 <b>After Claim:</b> {format_number(balance - min_balance)} pts\n\n"
        "🎁 You will receive:\n"
        "   • One unused Telegram Premium reward code\n"
        "   • Step-by-step redemption tutorial\n\n"
        "⚠️ <b>This action cannot be undone.</b>\nAre you sure?"
    )
    await cb.message.edit_text(
        text, parse_mode="HTML", reply_markup=confirm_claim_kb()
    )


@router.callback_query(F.data == "do_claim")
async def cb_do_claim(cb: CallbackQuery, db: Database, bot: Bot) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        return

    min_balance = int(await db.get_setting("min_premium_balance", "500"))

    # ── Single atomic transaction: re-verify + deduct + assign + record ────
    code_row = await db.claim_premium_atomic(user["id"], min_balance)

    if code_row is None:
        # Re-fetch state to give the user the right error message
        wallet = await db.get_wallet(user["id"])
        if wallet.get("balance", 0) < min_balance:
            await cb.message.edit_text(
                "❌ <b>Insufficient balance.</b> Please earn more points first.",
                parse_mode="HTML",
                reply_markup=back_to_menu_kb(),
            )
        else:
            await cb.message.edit_text(
                "😔 <b>No reward codes available.</b> Please try again later.",
                parse_mode="HTML",
                reply_markup=back_to_menu_kb(),
            )
        return

    success_text = (
        "👑 <b>CONGRATULATIONS !!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ <b>HOW TO ADD CC....</b>\n\n"
        "1. FIRST SEE FULL VIDEO. 🎬\n"
        "2. DOWNLOAD OLD VERSION OF NICEGRAM FROM CHROME. 🌐\n"
        "3. PROPERLY FILL CARD DETAILS IN THE BOT. 💳\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎁 <b>YOUR CARE AND DETAILS</b>\n\n"
        f"🔑 <b>CARD:</b> <code>{code_row['code']}</code>\n"
        "📌 <b>POSTCODE:</b> 90010 (THEN CLICK ON RANDOM ADRESS)"
    )

    # ── Send code + tutorial video together ────────────────────────────────
    video_file_id = await db.get_setting("tutorial_video_file_id", "")
    if video_file_id:
        try:
            await cb.message.edit_text(
                "✅ <b>Code claimed! Look below 👇</b>",
                parse_mode="HTML",
                reply_markup=back_to_menu_kb(),
            )
            await bot.send_video(
                chat_id=tg.id,
                video=video_file_id,
                caption=success_text,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error("Failed to send tutorial video: %s", e)
            # Fallback: send as text if video fails
            await cb.message.edit_text(
                success_text, parse_mode="HTML", reply_markup=back_to_menu_kb()
            )
    else:
        await cb.message.edit_text(
            success_text, parse_mode="HTML", reply_markup=back_to_menu_kb()
        )
