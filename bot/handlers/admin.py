import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramRetryAfter

from database import Database
from config import Config
from keyboards.admin_kb import (
    admin_main_kb,
    admin_back_kb,
    channels_kb,
    channel_type_kb,
    cancel_kb,
    withdrawal_action_kb,
)
from utils.helpers import escape_html, format_number, truncate

logger = logging.getLogger(__name__)
router = Router()


# ── FSM States ──────────────────────────────────────────────────────────────────

class AdminStates(StatesGroup):
    broadcast         = State()
    ban_user          = State()
    unban_user        = State()
    set_reward        = State()
    set_stars         = State()
    set_min_balance   = State()
    add_balance_id    = State()
    add_balance_amt   = State()
    set_dm_link       = State()
    add_channel_type    = State()   # waiting for public/private choice
    add_channel_public  = State()   # waiting for @username
    add_channel_private = State()   # waiting for t.me/+ invite link
    add_channel_chat_id = State()   # waiting for numeric chat id (-100xxx)
    add_channel_name    = State()   # waiting for display name (private only)


# ── Admin check ─────────────────────────────────────────────────────────────────

def is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


# ── /admin command ──────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await message.answer(
        "🛡️ <b>Admin Panel</b>\n\nWelcome, admin! Choose an action:",
        parse_mode="HTML",
        reply_markup=admin_main_kb(),
    )


@router.callback_query(F.data == "adm_panel")
async def cb_adm_panel(cb: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await state.clear()
    await cb.answer()
    await cb.message.edit_text(
        "🛡️ <b>Admin Panel</b>\n\nChoose an action:",
        parse_mode="HTML",
        reply_markup=admin_main_kb(),
    )


# ── Statistics ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_stats")
async def cb_adm_stats(cb: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    stats = await db.get_stats()
    reward_pts = await db.get_setting("referral_reward", "100")
    min_bal    = await db.get_setting("min_stars_balance", "500")
    stars_each = await db.get_setting("stars_per_claim", "50")

    text = (
        "📊 <b>Bot Statistics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Total Users:</b>        {format_number(stats['total_users'])}\n"
        f"🆕 <b>New Today:</b>          {format_number(stats['new_today'])}\n"
        f"🚫 <b>Banned Users:</b>       {format_number(stats['banned_users'])}\n"
        f"🔗 <b>Total Referrals:</b>    {format_number(stats['total_referrals'])}\n\n"
        f"⏳ <b>Pending Withdrawals:</b> {format_number(stats['pending_withdrawals'])}\n"
        f"✅ <b>Approved:</b>           {format_number(stats['approved_withdrawals'])}\n"
        f"⭐ <b>Total Stars Sent:</b>   {format_number(stats['total_stars_sent'])}\n"
        f"💰 <b>Points Distributed:</b> {format_number(stats['total_points'])}\n\n"
        f"⚙️ <b>Referral Reward:</b>   {reward_pts} pts\n"
        f"💎 <b>Min Balance:</b>        {min_bal} pts\n"
        f"⭐ <b>Stars per Claim:</b>    {stars_each} ⭐"
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())


# ── Users ───────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_users")
async def cb_adm_users(cb: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    users = await db.get_all_users()
    lines = []
    for u in users[:30]:
        uname = f"@{u['username']}" if u.get("username") else "—"
        banned = " 🚫" if u.get("is_banned") else ""
        lines.append(
            f"• <code>{u['telegram_id']}</code> — {escape_html(truncate(u['first_name'], 20))} "
            f"({escape_html(uname)}){banned}"
        )
    text = (
        f"👥 <b>Users ({len(users)} total)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        + ("\n".join(lines) if lines else "No users yet.")
        + ("\n\n<i>Showing first 30</i>" if len(users) > 30 else "")
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())


# ── Leaderboard ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_leaderboard")
async def cb_adm_leaderboard(cb: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    top = await db.get_top_referrers(10)
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [
        f"{medals[i]} {escape_html(truncate(r['first_name'], 20))} — {r['ref_count']} refs | {format_number(r['balance'])} pts"
        for i, r in enumerate(top)
    ]
    text = (
        "🏆 <b>Top Referrers</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        + ("\n".join(lines) if lines else "No referrals yet.")
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())


# ── Broadcast ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_broadcast")
async def cb_adm_broadcast(cb: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.broadcast)
    await cb.message.edit_text(
        "📢 <b>Broadcast Message</b>\n\n"
        "Send the message you want to broadcast to all users.\n"
        "Supports HTML formatting.\n\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.broadcast)
async def do_broadcast(message: Message, db: Database, bot: Bot, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    users = await db.get_all_users()
    text = message.html_text or message.text or ""
    success, fail = 0, 0
    status_msg = await message.answer(f"📤 Broadcasting to {len(users)} users…", parse_mode="HTML")

    async def send_to_user(u):
        nonlocal success, fail
        for _ in range(3):
            try:
                await bot.send_message(u["telegram_id"], text, parse_mode="HTML")
                success += 1
                return
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except Exception:
                break
        fail += 1

    chunk_size = 30
    for i in range(0, len(users), chunk_size):
        await asyncio.gather(*[send_to_user(u) for u in users[i:i + chunk_size]])
        await asyncio.sleep(1.0)

    await db.save_broadcast(text, message.from_user.id, success, fail)
    await status_msg.edit_text(
        f"✅ <b>Broadcast Complete</b>\n\n✉️ Sent: {success}\n❌ Failed: {fail}",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


# ── Ban / Unban ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_ban")
async def cb_adm_ban(cb: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.ban_user)
    await cb.message.edit_text(
        "🚫 <b>Ban User</b>\n\nSend the Telegram ID of the user to ban.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.ban_user)
async def do_ban(message: Message, db: Database, bot: Bot, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Invalid ID.", reply_markup=admin_back_kb())
        return
    ok = await db.ban_user(tg_id)
    if ok:
        try:
            await bot.send_message(tg_id, "🚫 <b>You have been banned from this bot.</b>", parse_mode="HTML")
        except Exception:
            pass
        await message.answer(f"✅ User <code>{tg_id}</code> banned.", parse_mode="HTML", reply_markup=admin_back_kb())
    else:
        await message.answer(f"❌ User <code>{tg_id}</code> not found.", parse_mode="HTML", reply_markup=admin_back_kb())


@router.callback_query(F.data == "adm_unban")
async def cb_adm_unban(cb: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.unban_user)
    await cb.message.edit_text(
        "✅ <b>Unban User</b>\n\nSend the Telegram ID of the user to unban.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.unban_user)
async def do_unban(message: Message, db: Database, bot: Bot, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Invalid ID.", reply_markup=admin_back_kb())
        return
    ok = await db.unban_user(tg_id)
    if ok:
        try:
            await bot.send_message(tg_id, "✅ <b>Your ban has been lifted. You can use the bot again!</b>", parse_mode="HTML")
        except Exception:
            pass
        await message.answer(f"✅ User <code>{tg_id}</code> unbanned.", parse_mode="HTML", reply_markup=admin_back_kb())
    else:
        await message.answer(f"❌ User <code>{tg_id}</code> not found.", parse_mode="HTML", reply_markup=admin_back_kb())


# ── Star Withdrawals ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_pending_withdrawals")
async def cb_adm_pending(cb: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    pending = await db.get_pending_withdrawals()
    if not pending:
        await cb.message.edit_text(
            "⏳ <b>Pending Withdrawals</b>\n\n✅ No pending requests!",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
        return
    for w in pending[:10]:
        uname = f"@{w['username']}" if w.get("username") else f"ID:{w['telegram_id']}"
        text = (
            f"🔔 <b>Withdrawal Request #{w['id']}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>User:</b> {escape_html(w['first_name'])} ({escape_html(uname)})\n"
            f"🆔 <b>TG ID:</b> <code>{w['telegram_id']}</code>\n"
            f"⭐ <b>Stars:</b> {w['stars_amount']} ⭐\n"
            f"💸 <b>Points Spent:</b> {format_number(w['points_spent'])}\n"
            f"📅 <b>Date:</b> {str(w['created_at'])[:10]}\n\n"
            f"Send stars to <code>{w['telegram_id']}</code> then approve below."
        )
        await cb.message.answer(text, parse_mode="HTML", reply_markup=withdrawal_action_kb(w["id"]))
    if len(pending) > 10:
        await cb.message.answer(f"<i>Showing first 10 of {len(pending)} pending.</i>", parse_mode="HTML", reply_markup=admin_back_kb())
    else:
        await cb.message.answer("✅ All pending requests shown above.", reply_markup=admin_back_kb())


@router.callback_query(F.data == "adm_all_withdrawals")
async def cb_adm_all_withdrawals(cb: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    withdrawals = await db.get_all_withdrawals(limit=30)
    status_icons = {"pending": "⏳", "approved": "✅", "rejected": "❌"}
    lines = []
    for w in withdrawals:
        icon = status_icons.get(w["status"], "❓")
        uname = f"@{w['username']}" if w.get("username") else str(w["telegram_id"])
        lines.append(
            f"{icon} #{w['id']} — {escape_html(truncate(w['first_name'], 15))} ({escape_html(uname)}) "
            f"— {w['stars_amount']}⭐ — {str(w['created_at'])[:10]}"
        )
    text = (
        f"📜 <b>All Withdrawals (last {len(withdrawals)})</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        + ("\n".join(lines) if lines else "No withdrawals yet.")
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())


@router.callback_query(F.data.startswith("adm_approve_"))
async def cb_adm_approve(cb: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    withdrawal_id = int(cb.data[len("adm_approve_"):])
    w = await db.get_withdrawal(withdrawal_id)
    ok = await db.approve_withdrawal(withdrawal_id, cb.from_user.id)
    if ok:
        await cb.answer("✅ Approved!", show_alert=False)
        await cb.message.edit_text(
            f"✅ <b>Withdrawal #{withdrawal_id} Approved</b>\n\n"
            f"User <code>{w['telegram_id'] if w else '?'}</code> notified.",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
        if w:
            try:
                await bot.send_message(
                    w["telegram_id"],
                    f"🎉 <b>Stars Sent!</b>\n\n"
                    f"Your withdrawal request #{withdrawal_id} has been approved!\n"
                    f"⭐ <b>{w['stars_amount']} Telegram Stars</b> have been sent to your account.",
                    parse_mode="HTML",
                )
            except Exception:
                pass
    else:
        await cb.answer("❌ Already processed.", show_alert=True)


@router.callback_query(F.data.startswith("adm_reject_"))
async def cb_adm_reject(cb: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    withdrawal_id = int(cb.data[len("adm_reject_"):])
    w = await db.reject_withdrawal(withdrawal_id, cb.from_user.id)
    if w:
        await cb.answer("❌ Rejected & refunded.", show_alert=False)
        await cb.message.edit_text(
            f"❌ <b>Withdrawal #{withdrawal_id} Rejected</b>\n\n"
            f"{format_number(w['points_spent'])} pts refunded to user.",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
        try:
            user_row = await db.get_user_by_id(w["user_id"])
            if user_row:
                await bot.send_message(
                    user_row["telegram_id"],
                    f"❌ <b>Withdrawal #{withdrawal_id} Rejected</b>\n\n"
                    f"Your request was rejected. <b>{format_number(w['points_spent'])} points</b> have been refunded.",
                    parse_mode="HTML",
                )
        except Exception:
            pass
    else:
        await cb.answer("❌ Already processed.", show_alert=True)


# ── Settings ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_set_reward")
async def cb_adm_set_reward(cb: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.set_reward)
    await cb.message.edit_text(
        "⚙️ <b>Set Referral Reward</b>\n\nSend the new points amount per referral (e.g. 100).",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.set_reward)
async def do_set_reward(message: Message, db: Database, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    try:
        val = int(message.text.strip())
        assert val > 0
    except (ValueError, AssertionError):
        await message.answer("❌ Send a valid positive number.", reply_markup=cancel_kb())
        return
    await db.set_setting("referral_reward", str(val))
    await message.answer(f"✅ Referral reward set to <b>{val} pts</b>.", parse_mode="HTML", reply_markup=admin_back_kb())


@router.callback_query(F.data == "adm_set_stars")
async def cb_adm_set_stars(cb: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.set_stars)
    await cb.message.edit_text(
        "⭐ <b>Set Stars per Claim</b>\n\nSend how many Telegram Stars users get per withdrawal (e.g. 50).",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.set_stars)
async def do_set_stars(message: Message, db: Database, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    try:
        val = int(message.text.strip())
        assert val > 0
    except (ValueError, AssertionError):
        await message.answer("❌ Send a valid positive number.", reply_markup=cancel_kb())
        return
    await db.set_setting("stars_per_claim", str(val))
    await message.answer(f"✅ Stars per claim set to <b>{val} ⭐</b>.", parse_mode="HTML", reply_markup=admin_back_kb())


@router.callback_query(F.data == "adm_set_min")
async def cb_adm_set_min(cb: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.set_min_balance)
    await cb.message.edit_text(
        "💎 <b>Set Minimum Balance</b>\n\nSend the minimum points required to withdraw Stars (e.g. 500).",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.set_min_balance)
async def do_set_min(message: Message, db: Database, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    try:
        val = int(message.text.strip())
        assert val > 0
    except (ValueError, AssertionError):
        await message.answer("❌ Send a valid positive number.", reply_markup=cancel_kb())
        return
    await db.set_setting("min_stars_balance", str(val))
    await message.answer(f"✅ Min balance set to <b>{val} pts</b>.", parse_mode="HTML", reply_markup=admin_back_kb())


# ── Add Balance ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_add_balance")
async def cb_adm_add_balance(cb: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.add_balance_id)
    await cb.message.edit_text(
        "💰 <b>Add Balance</b>\n\nStep 1/2: Send the <b>Telegram ID</b> of the user.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.add_balance_id)
async def do_add_balance_id(message: Message, db: Database, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Invalid ID.", reply_markup=cancel_kb())
        return
    user = await db.get_user(tg_id)
    if not user:
        await message.answer(f"❌ User <code>{tg_id}</code> not found.", parse_mode="HTML", reply_markup=cancel_kb())
        return
    await state.update_data(target_tg_id=tg_id, target_user_id=user["id"], target_name=user["first_name"])
    await state.set_state(AdminStates.add_balance_amt)
    await message.answer(
        f"💰 <b>Add Balance</b>\n\nStep 2/2: Found user <b>{escape_html(user['first_name'])}</b>.\nSend the points amount to add.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.add_balance_amt)
async def do_add_balance_amt(message: Message, db: Database, bot: Bot, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    try:
        amount = int(message.text.strip())
        assert amount > 0
    except (ValueError, AssertionError):
        await message.answer("❌ Send a valid positive number.", reply_markup=cancel_kb())
        return
    data = await state.get_data()
    await state.clear()
    user_id = data["target_user_id"]
    tg_id = data["target_tg_id"]
    name = data["target_name"]
    await db.add_to_wallet(user_id, amount, "other")
    wallet = await db.get_wallet(user_id)
    await message.answer(
        f"✅ <b>{format_number(amount)} pts</b> added to <b>{escape_html(name)}</b>!\n"
        f"💰 New Balance: <b>{format_number(wallet.get('balance', 0))} pts</b>",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    try:
        await bot.send_message(
            tg_id,
            f"🎉 <b>Balance Added!</b>\n\nAdmin added <b>{format_number(amount)} points</b>!\n"
            f"💰 <b>New Balance:</b> {format_number(wallet.get('balance', 0))} pts",
            parse_mode="HTML",
        )
    except Exception:
        pass


# ── DM Link ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_set_dm_link")
async def cb_adm_set_dm_link(cb: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.set_dm_link)
    await cb.message.edit_text(
        "🔗 <b>Set DM Link</b>\n\nSend the t.me link for your DM (e.g. https://t.me/yourusername).",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.set_dm_link)
async def do_set_dm_link(message: Message, db: Database, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    link = (message.text or "").strip()
    await db.set_setting("dm_link", link)
    await message.answer(f"✅ DM link set to: {escape_html(link)}", parse_mode="HTML", reply_markup=admin_back_kb())


# ── Force Join Channels ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_channels")
async def cb_adm_channels(cb: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    channels = await db.get_channels()
    count = len(channels)
    text = f"📡 <b>Force Join Channels ({count})</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for ch in channels:
        title = escape_html(ch.get("channel_title") or ch.get("channel_id"))
        uname = ch.get("channel_username") or "—"
        text += f"• {title} ({escape_html(uname)})\n"
    if not channels:
        text += "No channels added yet.\n"
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=channels_kb(channels))


@router.callback_query(F.data == "adm_addchan")
async def cb_adm_addchan(cb: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.add_channel_type)
    await cb.message.edit_text(
        "📡 <b>Add Channel</b>\n\n"
        "Channel ka type select karo:",
        parse_mode="HTML",
        reply_markup=channel_type_kb(),
    )


# ── Public channel flow ────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_chan_public", AdminStates.add_channel_type)
async def cb_chan_public(cb: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.add_channel_public)
    await cb.message.edit_text(
        "🌐 <b>Public Channel</b>\n\n"
        "Channel ka <b>@username</b> bhejo:\n"
        "Example: <code>@mychannel</code>",
        parse_mode="HTML",
        reply_markup=cancel_kb("adm_channels"),
    )


@router.message(AdminStates.add_channel_public)
async def do_add_channel_public(message: Message, db: Database, state: FSMContext, config: Config, bot: Bot) -> None:
    if not is_admin(message.from_user.id, config):
        return
    username = (message.text or "").strip()
    if not username.startswith("@"):
        await message.answer(
            "❌ Username <b>@</b> se shuru hona chahiye.\nExample: <code>@mychannel</code>",
            parse_mode="HTML",
            reply_markup=cancel_kb("adm_channels"),
        )
        return

    # Try to fetch channel title automatically
    title = username
    try:
        chat = await bot.get_chat(username)
        title = chat.title or username
    except Exception:
        pass

    await state.clear()
    ok = await db.add_channel(channel_id=username, username=username, title=title, invite_link=None)
    if ok:
        await message.answer(
            f"✅ Public channel <b>{escape_html(title)}</b> add ho gaya!",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
    else:
        await message.answer("❌ Channel already exists ya error aaya.", reply_markup=admin_back_kb())


# ── Private channel flow ───────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_chan_private", AdminStates.add_channel_type)
async def cb_chan_private(cb: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.add_channel_private)
    await cb.message.edit_text(
        "🔒 <b>Private Channel</b>\n\n"
        "Channel ka <b>invite link</b> bhejo:\n"
        "Example: <code>https://t.me/+xxxxxxxxxxxx</code>\n\n"
        "<i>⚠️ Bot ko us channel mein Admin hona chahiye</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb("adm_channels"),
    )


@router.message(AdminStates.add_channel_private)
async def do_add_channel_private(message: Message, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    link = (message.text or "").strip()
    if "t.me/+" not in link and "t.me/joinchat/" not in link:
        await message.answer(
            "❌ Sahi invite link bhejo.\nExample: <code>https://t.me/+xxxxxxxxxxxx</code>",
            parse_mode="HTML",
            reply_markup=cancel_kb("adm_channels"),
        )
        return
    if not link.startswith("http"):
        link = f"https://{link}"
    await state.update_data(invite_link=link)
    await state.set_state(AdminStates.add_channel_chat_id)
    await message.answer(
        "🔒 <b>Private Channel — Step 2/3</b>\n\n"
        "Ab channel ka <b>numeric ID</b> bhejo.\n"
        "Example: <code>-1001234567890</code>\n\n"
        "<b>ID kaise milega?</b>\n"
        "Channel mein koi bhi message forward karo <b>@userinfobot</b> pe — "
        "woh channel ID bata dega.",
        parse_mode="HTML",
        reply_markup=cancel_kb("adm_channels"),
    )


@router.message(AdminStates.add_channel_chat_id)
async def do_add_channel_chat_id(message: Message, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    raw = (message.text or "").strip()
    # Accept formats: -1001234567890 or 1001234567890
    try:
        chat_id = int(raw)
        if chat_id > 0:
            chat_id = -chat_id  # ensure negative
    except ValueError:
        await message.answer(
            "❌ Sirf numeric ID bhejo.\nExample: <code>-1001234567890</code>",
            parse_mode="HTML",
            reply_markup=cancel_kb("adm_channels"),
        )
        return
    await state.update_data(chat_id=str(chat_id))
    await state.set_state(AdminStates.add_channel_name)
    await message.answer(
        "🔒 <b>Private Channel — Step 3/3</b>\n\n"
        "Ab channel ka <b>display name</b> bhejo\n"
        "(jo users ko dikhe, e.g. <code>My VIP Channel</code>):",
        parse_mode="HTML",
        reply_markup=cancel_kb("adm_channels"),
    )


@router.message(AdminStates.add_channel_name)
async def do_add_channel_name(message: Message, db: Database, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    data = await state.get_data()
    await state.clear()
    invite_link = data.get("invite_link", "")
    chat_id = data.get("chat_id", invite_link)   # numeric id for membership check
    display_name = (message.text or "").strip() or invite_link

    ok = await db.add_channel(channel_id=chat_id, username=None, title=display_name, invite_link=invite_link)
    if ok:
        await message.answer(
            f"✅ Private channel <b>{escape_html(display_name)}</b> add ho gaya!",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
    else:
        await message.answer("❌ Channel already exists ya error aaya.", reply_markup=admin_back_kb())


@router.callback_query(F.data.startswith("adm_rmchan_"))
async def cb_adm_rmchan(cb: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    channel_id = cb.data[len("adm_rmchan_"):]
    ok = await db.remove_channel(channel_id)
    await cb.answer("✅ Removed." if ok else "❌ Not found.", show_alert=not ok)
    channels = await db.get_channels()
    text = f"📡 <b>Force Join Channels ({len(channels)})</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for ch in channels:
        text += f"• {escape_html(ch.get('channel_title') or ch.get('channel_id'))} ({escape_html(ch.get('channel_username') or '—')})\n"
    if not channels:
        text += "No channels.\n"
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=channels_kb(channels))


# ── Cancel ─────────────────────────────────────────────────────────────────────

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    await message.answer("❌ Action cancelled.", reply_markup=admin_main_kb(), parse_mode="HTML")
