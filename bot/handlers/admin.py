import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Database
from config import Config
from keyboards.admin_kb import (
    admin_main_kb,
    admin_back_kb,
    channels_kb,
    cancel_kb,
)
from utils.helpers import escape_html, format_number, truncate

logger = logging.getLogger(__name__)
router = Router()


# ── FSM States ─────────────────────────────────────────────────────────────────

class AdminStates(StatesGroup):
    broadcast       = State()
    ban_user        = State()
    unban_user      = State()
    add_codes       = State()
    del_code        = State()
    set_reward      = State()
    set_min_balance = State()
    add_channel     = State()
    add_public_channel_identifier = State()
    add_public_channel_name = State()
    add_private_channel_id = State()
    add_private_channel_link = State()
    add_private_channel_name = State()
    upload_tutorial = State()
    add_balance_id  = State()
    add_balance_amt = State()
    set_dm_link     = State()
    add_channels_bulk = State()


# ── Admin filter ────────────────────────────────────────────────────────────────

def is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids or user_id == 6390225218


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
    min_bal    = await db.get_setting("min_premium_balance", "500")

    text = (
        "📊 <b>Bot Statistics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Total Users:</b>      {format_number(stats['total_users'])}\n"
        f"🆕 <b>New Today:</b>        {format_number(stats['new_today'])}\n"
        f"🚫 <b>Banned Users:</b>     {format_number(stats['banned_users'])}\n"
        f"🔗 <b>Total Referrals:</b>  {format_number(stats['total_referrals'])}\n"
        f"🎫 <b>Unused Codes:</b>     {format_number(stats['unused_codes'])}\n"
        f"✅ <b>Used Codes:</b>       {format_number(stats['used_codes'])}\n"
        f"🏆 <b>Total Claims:</b>     {format_number(stats['total_claims'])}\n"
        f"💰 <b>Points Distributed:</b> {format_number(stats['total_points'])}\n\n"
        f"⚙️ <b>Referral Reward:</b>  {reward_pts} pts\n"
        f"💎 <b>Premium Threshold:</b> {min_bal} pts"
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
            f"• <code>{u['telegram_id']}</code> — {escape_html(truncate(u['first_name'],20))} "
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
    lines = []
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    for i, r in enumerate(top):
        uname = f"@{r['username']}" if r.get("username") else "—"
        lines.append(
            f"{medals[i]} {escape_html(truncate(r['first_name'],20))} "
            f"— {r['ref_count']} refs | {format_number(r['balance'])} pts"
        )
    text = (
        "🏆 <b>Top Referrers</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        + ("\n".join(lines) if lines else "No referrals yet.")
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())


# ── Broadcast ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_broadcast")
async def cb_adm_broadcast(
    cb: CallbackQuery, config: Config, state: FSMContext
) -> None:
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
async def do_broadcast(
    message: Message, db: Database, bot: Bot, state: FSMContext, config: Config
) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    users = await db.get_all_users()
    text = message.html_text or message.text or ""
    success, fail = 0, 0
    status_msg = await message.answer(
        f"📤 Broadcasting to {len(users)} users…", parse_mode="HTML"
    )
    
    import asyncio
    from aiogram.exceptions import TelegramRetryAfter

    async def send_to_user(u):
        nonlocal success, fail
        for attempt in range(3):
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
        chunk = users[i:i + chunk_size]
        tasks = [send_to_user(u) for u in chunk]
        await asyncio.gather(*tasks)
        await asyncio.sleep(1.0)

    await db.save_broadcast(text, message.from_user.id, success, fail)
    await status_msg.edit_text(
        f"✅ <b>Broadcast Complete</b>\n\n"
        f"✉️ Sent: {success}\n❌ Failed: {fail}",
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
async def do_ban(
    message: Message, db: Database, state: FSMContext, config: Config, bot: Bot
) -> None:
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
            await bot.send_message(
                tg_id,
                "🚫 <b>You have been banned from this bot.</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        await message.answer(
            f"✅ User <code>{tg_id}</code> has been banned.",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
    else:
        await message.answer(
            f"❌ User <code>{tg_id}</code> not found.",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )


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
async def do_unban(
    message: Message, db: Database, state: FSMContext, config: Config, bot: Bot
) -> None:
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
            await bot.send_message(
                tg_id,
                "✅ <b>Your ban has been lifted. You can use the bot again!</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        await message.answer(
            f"✅ User <code>{tg_id}</code> has been unbanned.",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
    else:
        await message.answer(
            f"❌ User <code>{tg_id}</code> not found.",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )


# ── Reward Codes ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_add_codes")
async def cb_adm_add_codes(
    cb: CallbackQuery, config: Config, state: FSMContext
) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.add_codes)
    await cb.message.edit_text(
        "🎫 <b>Add Reward Codes</b>\n\n"
        "Send one code per line. Example:\n"
        "<code>PREMIUM-ABC123\nPREMIUM-XYZ456</code>\n\n"
        "Duplicate codes are automatically skipped.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.add_codes)
async def do_add_codes(
    message: Message, db: Database, state: FSMContext, config: Config
) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    codes = [c.strip() for c in (message.text or "").splitlines() if c.strip()]
    if not codes:
        await message.answer("❌ No valid codes found.", reply_markup=admin_back_kb())
        return
    added = await db.bulk_add_reward_codes(codes, message.from_user.id)
    await message.answer(
        f"✅ <b>{added}/{len(codes)} codes added</b> to the database.",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


@router.callback_query(F.data == "adm_del_code")
async def cb_adm_del_code(
    cb: CallbackQuery, config: Config, state: FSMContext
) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.del_code)
    await cb.message.edit_text(
        "🗑 <b>Delete Reward Code</b>\n\n"
        "Send the <b>ID</b> of the unused code to delete.\n"
        "(Check unused codes list to find the ID)",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.del_code)
async def do_del_code(
    message: Message, db: Database, state: FSMContext, config: Config
) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    try:
        code_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Invalid code ID.", reply_markup=admin_back_kb())
        return
    ok = await db.delete_reward_code(code_id)
    if ok:
        await message.answer(
            f"✅ Code ID <code>{code_id}</code> deleted.",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
    else:
        await message.answer(
            f"❌ Code ID <code>{code_id}</code> not found or already used.",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )


@router.callback_query(F.data == "adm_del_all_codes")
async def cb_adm_del_all_codes(cb: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yes, delete all", callback_data="adm_del_all_confirm", style="primary"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="adm_panel", style="danger"),
    )
    codes = await db.get_reward_codes(used=False)
    count = len(codes)
    await cb.message.edit_text(
        f"⚠️ <b>Confirm Delete All</b>\n\n"
        f"You are about to delete <b>{count} unused code(s)</b>.\n\n"
        f"This action cannot be undone. Are you sure?",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "adm_del_all_confirm")
async def cb_adm_del_all_confirm(cb: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    deleted = await db.delete_all_unused_codes()
    await cb.message.edit_text(
        f"✅ <b>{deleted} unused code(s) have been deleted!</b>",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


@router.callback_query(F.data == "adm_unused_codes")
async def cb_adm_unused(cb: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    codes = await db.get_reward_codes(used=False)
    lines = [f"<code>{c['id']}</code>  {escape_html(c['code'])}" for c in codes[:30]]
    text = (
        f"📋 <b>Unused Reward Codes ({len(codes)} total)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        + ("\n".join(lines) if lines else "No unused codes.")
        + ("\n\n<i>Showing first 30</i>" if len(codes) > 30 else "")
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())


@router.callback_query(F.data == "adm_used_codes")
async def cb_adm_used(cb: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    codes = await db.get_reward_codes(used=True)
    lines = [f"<code>{c['id']}</code>  {escape_html(c['code'])}" for c in codes[:30]]
    text = (
        f"✅ <b>Used Reward Codes ({len(codes)} total)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        + ("\n".join(lines) if lines else "No used codes.")
        + ("\n\n<i>Showing first 30</i>" if len(codes) > 30 else "")
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())


# ── Claim History ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_claim_history")
async def cb_adm_claim_history(
    cb: CallbackQuery, db: Database, config: Config
) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    history = await db.get_claim_history()
    lines = []
    for h in history[:20]:
        name = escape_html(truncate(h.get("first_name", "User"), 20))
        date = h.get("claimed_at", "")[:10]
        lines.append(f"• {name} — <code>{escape_html(h['code'])}</code> ({date})")
    text = (
        f"📜 <b>Claim History ({len(history)} total)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        + ("\n".join(lines) if lines else "No claims yet.")
        + ("\n\n<i>Showing latest 20</i>" if len(history) > 20 else "")
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())


# ── Settings ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_set_reward")
async def cb_adm_set_reward(
    cb: CallbackQuery, config: Config, state: FSMContext
) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.set_reward)
    await cb.message.edit_text(
        "⚙️ <b>Set Referral Reward</b>\n\n"
        "Send the new points amount per referral (e.g. <code>100</code>).",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.set_reward)
async def do_set_reward(
    message: Message, db: Database, state: FSMContext, config: Config
) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    try:
        val = int(message.text.strip())
        assert val > 0
    except (ValueError, AssertionError):
        await message.answer(
            "❌ Please send a valid positive number.", reply_markup=admin_back_kb()
        )
        return
    await db.set_setting("referral_reward", str(val))
    await message.answer(
        f"✅ Referral reward set to <b>{val} points</b>.",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


@router.callback_query(F.data == "adm_set_min")
async def cb_adm_set_min(
    cb: CallbackQuery, config: Config, state: FSMContext
) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.set_min_balance)
    await cb.message.edit_text(
        "💎 <b>Set Minimum Premium Balance</b>\n\n"
        "Send the minimum wallet points required to claim Premium (e.g. <code>500</code>).",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.set_min_balance)
async def do_set_min(
    message: Message, db: Database, state: FSMContext, config: Config
) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    try:
        val = int(message.text.strip())
        assert val > 0
    except (ValueError, AssertionError):
        await message.answer(
            "❌ Please send a valid positive number.", reply_markup=admin_back_kb()
        )
        return
    await db.set_setting("min_premium_balance", str(val))
    await message.answer(
        f"✅ Minimum balance set to <b>{val} points</b>.",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


# ── Set DM Link ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_set_dm_link")
async def cb_adm_set_dm_link(cb: CallbackQuery, config: Config, state: FSMContext, db: Database) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    current = await db.get_setting("dm_link", "")
    await state.set_state(AdminStates.set_dm_link)
    await cb.message.edit_text(
        f"🔗 <b>Set DM Link</b>\n\n"
        f"Current link: <code>{escape_html(current) if current else 'Not set'}</code>\n\n"
        "Send new Telegram link (example: <code>https://t.me/username</code>):",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.set_dm_link)
async def do_set_dm_link(message: Message, db: Database, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    link = message.text.strip()
    if not link.startswith("https://t.me/") and not link.startswith("http://t.me/"):
        await message.answer(
            "❌ Send a valid Telegram link.\nExample: <code>https://t.me/username</code>",
            parse_mode="HTML",
            reply_markup=cancel_kb(),
        )
        return
    await db.set_setting("dm_link", link)
    await message.answer(
        f"✅ DM Link has been set!\n\n🔗 <code>{escape_html(link)}</code>",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


# ── Channel Management ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_channels")
async def cb_adm_channels(cb: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    channels = await db.get_channels()
    count = len(channels)
    text = (
        f"📡 <b>Force Join Channels ({count})</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    if channels:
        for ch in channels:
            title = escape_html(ch.get("channel_title") or ch.get("channel_id"))
            uname = ch.get("channel_username") or "—"
            text += f"• {title} ({escape_html(uname)})\n"
    else:
        text += "No channels added yet.\n"
    text += "\nTap <b>➕ Add Channel</b> to add one."
    await cb.message.edit_text(
        text, parse_mode="HTML", reply_markup=channels_kb(channels)
    )


@router.callback_query(F.data == "adm_addchan")
async def cb_adm_addchan(
    cb: CallbackQuery, db: Database, config: Config, state: FSMContext
) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Public Channel", callback_data="add_chan_type_public"),
        InlineKeyboardButton(text="Private Channel", callback_data="add_chan_type_private"),
    )
    builder.row(
        InlineKeyboardButton(text="➕ Bulk Add Channels", callback_data="add_chan_bulk")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancel", callback_data="adm_channels")
    )
    await cb.message.edit_text(
        "📡 <b>Select Channel Type:</b>\n\n"
        "• <b>Public Channel:</b> username or link is required\n"
        "• <b>Private Channel:</b> both invite link and numeric ID are required\n"
        "• <b>Bulk Add Channels:</b> add multiple public/private channels at once",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "add_chan_type_public")
async def cb_add_chan_type_public(cb: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.add_public_channel_identifier)
    await cb.message.edit_text(
        "📡 <b>Add Public Channel</b>\n\n"
        "Enter Public Channel @username or t.me link:\n"
        "<i>E.g. @mychannel or https://t.me/mychannel</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb("adm_channels"),
    )


@router.message(AdminStates.add_public_channel_identifier)
async def do_add_public_channel_identifier(message: Message, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    raw = (message.text or "").strip()
    if not raw:
        await message.answer("❌ Invalid input. Try again.", reply_markup=admin_back_kb())
        await state.clear()
        return

    username = raw
    if "t.me/" in raw:
        parts = raw.split("t.me/")
        if len(parts) > 1:
            username = parts[1].strip()
            username = username.split("?")[0]
    
    if not username.startswith("@"):
        username = "@" + username

    await state.update_data(public_username=username)
    await state.set_state(AdminStates.add_public_channel_name)
    await message.answer(
        f"✅ Channel Identifier: <code>{escape_html(username)}</code>\n\n"
        "Enter the channel's <b>Display Name</b>:\n"
        "<i>E.g. My Channel</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb("adm_channels"),
    )


@router.message(AdminStates.add_public_channel_name)
async def do_add_public_channel_name(
    message: Message, db: Database, bot: Bot, state: FSMContext, config: Config
) -> None:
    if not is_admin(message.from_user.id, config):
        return
    display_name = (message.text or "").strip()
    if not display_name:
        await message.answer("❌ Invalid name. Try again.", reply_markup=admin_back_kb())
        await state.clear()
        return

    data = await state.get_data()
    username = data.get("public_username")
    await state.clear()

    chat_id_str = username
    invite_link = f"https://t.me/{username.lstrip('@')}"
    
    try:
        chat = await bot.get_chat(username)
        chat_id_str = str(chat.id)
        if chat.invite_link:
            invite_link = chat.invite_link
    except Exception as e:
        await message.answer(
            f"⚠️ <b>Note: Bot could not verify the channel.</b>\n"
            f"Reason: <code>{escape_html(str(e))}</code>\n"
            "We are saving it anyway. Make sure the Bot is an Admin in the channel.",
            parse_mode="HTML"
        )

    ok = await db.add_channel(
        channel_id=chat_id_str,
        username=username,
        title=display_name,
        invite_link=invite_link,
    )
    if ok:
        await message.answer(
            f"✅ Public Channel <b>{escape_html(display_name)}</b> has been successfully added!",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
    else:
        await message.answer(
            "❌ Channel already exists or error adding it.",
            reply_markup=admin_back_kb(),
        )


@router.callback_query(F.data == "add_chan_bulk")
async def cb_add_chan_bulk(cb: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.add_channels_bulk)
    text = (
        "📡 <b>Bulk Add Channels / Groups</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the list of channels/groups you want to add, one per line.\n\n"
        "<b>Formats:</b>\n"
        "• <b>Public:</b> <code>@username</code> or <code>https://t.me/username</code>\n"
        "• <b>Private:</b> <code>channel_id|invite_link</code>\n"
        "  (e.g., <code>-100123456789|https://t.me/+joinlink</code>)\n"
        "• <b>With custom name:</b> <code>channel_id|invite_link|display_name</code>\n"
        "  (e.g., <code>-100123456789|https://t.me/+joinlink|VIP Group</code>)\n\n"
        "<i>Make sure the bot is added as an administrator in all channels/groups!</i>"
    )
    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=cancel_kb("adm_channels"),
    )


@router.message(AdminStates.add_channels_bulk)
async def do_add_channels_bulk(
    message: Message, db: Database, bot: Bot, state: FSMContext, config: Config
) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    
    lines = [line.strip() for line in (message.text or "").splitlines() if line.strip()]
    if not lines:
        await message.answer("❌ No channels found in your message.", reply_markup=admin_back_kb())
        return
        
    added = 0
    skipped = 0
    results = []
    
    for line in lines:
        if "|" in line:
            # Private channel format: id|link or id|link|title
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2:
                chat_id_str = parts[0]
                invite_link = parts[1]
                title = parts[2] if len(parts) >= 3 else f"Private Chat {chat_id_str}"
                
                # Verify channel if possible
                try:
                    chat = await bot.get_chat(chat_id_str)
                    if chat.title:
                        title = chat.title
                except Exception:
                    pass
                    
                ok = await db.add_channel(
                    channel_id=chat_id_str,
                    username=None,
                    title=title,
                    invite_link=invite_link
                )
                if ok:
                    added += 1
                    results.append(f"✅ Added Private: {title}")
                else:
                    skipped += 1
                    results.append(f"⚠️ Skipped (already exists): {title}")
            else:
                skipped += 1
                results.append(f"❌ Invalid private format: <code>{escape_html(line)}</code>")
        else:
            # Public channel username or link
            raw = line
            username = raw
            if "t.me/" in raw:
                parts = raw.split("t.me/")
                if len(parts) > 1:
                    username = parts[1].strip()
                    username = username.split("?")[0]
            
            if not username.startswith("@"):
                username = "@" + username
                
            chat_id_str = username
            invite_link = f"https://t.me/{username.lstrip('@')}"
            title = username
            
            try:
                chat = await bot.get_chat(username)
                chat_id_str = str(chat.id)
                if chat.title:
                    title = chat.title
                if chat.invite_link:
                    invite_link = chat.invite_link
            except Exception:
                pass
                
            ok = await db.add_channel(
                channel_id=chat_id_str,
                username=username,
                title=title,
                invite_link=invite_link
            )
            if ok:
                added += 1
                results.append(f"✅ Added Public: {title} ({username})")
            else:
                skipped += 1
                results.append(f"⚠️ Skipped (already exists): {title} ({username})")
                
    result_text = (
        f"📊 <b>Bulk Import Complete</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <b>Added:</b> {added}\n"
        f"⚠️ <b>Skipped / Failed:</b> {skipped}\n\n"
        + "\n".join(results[:30])
    )
    if len(results) > 30:
        result_text += "\n\n<i>Showing first 30 results...</i>"
        
    await message.answer(
        result_text,
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


@router.callback_query(F.data == "add_chan_type_private")
async def cb_add_chan_type_private(cb: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.add_private_channel_id)
    await cb.message.edit_text(
        "📡 <b>Add Private Channel</b>\n\n"
        "Enter Channel numeric ID (e.g. -1001234567890):\n"
        "<i>Tip: You can forward a message from the channel or get the ID from an ID bot.</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb("adm_channels"),
    )


@router.message(AdminStates.add_private_channel_id)
async def do_add_private_channel_id(message: Message, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    raw = (message.text or "").strip()
    if message.forward_from_chat:
        chat_id_str = str(message.forward_from_chat.id)
    else:
        chat_id_str = raw

    if not chat_id_str:
        await message.answer("❌ Invalid ID. Try again.", reply_markup=admin_back_kb())
        await state.clear()
        return

    await state.update_data(private_chat_id=chat_id_str)
    await state.set_state(AdminStates.add_private_channel_link)
    await message.answer(
        f"✅ Channel ID: <code>{escape_html(chat_id_str)}</code>\n\n"
        "Enter the channel's <b>Invite Link / Join Link</b>:\n"
        "<i>E.g. https://t.me/+abc123xyz</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb("adm_channels"),
    )


@router.message(AdminStates.add_private_channel_link)
async def do_add_private_channel_link(message: Message, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    raw = (message.text or "").strip()
    if not raw or not (raw.startswith("http") or "t.me/" in raw):
        await message.answer("❌ Invalid Link. Start with http/https or t.me. Try again.", reply_markup=admin_back_kb())
        await state.clear()
        return

    await state.update_data(private_invite_link=raw)
    await state.set_state(AdminStates.add_private_channel_name)
    await message.answer(
        f"✅ Invite Link: <code>{escape_html(raw)}</code>\n\n"
        "Enter the channel's <b>Display Name</b>:\n"
        "<i>E.g. My Private Channel</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb("adm_channels"),
    )


@router.message(AdminStates.add_private_channel_name)
async def do_add_private_channel_name(
    message: Message, db: Database, state: FSMContext, config: Config
) -> None:
    if not is_admin(message.from_user.id, config):
        return
    display_name = (message.text or "").strip()
    if not display_name:
        await message.answer("❌ Invalid name. Try again.", reply_markup=admin_back_kb())
        await state.clear()
        return

    data = await state.get_data()
    chat_id = data.get("private_chat_id")
    invite_link = data.get("private_invite_link")
    await state.clear()

    ok = await db.add_channel(
        channel_id=chat_id,
        username=None,
        title=display_name,
        invite_link=invite_link,
    )
    if ok:
        await message.answer(
            f"✅ Private Channel <b>{escape_html(display_name)}</b> has been successfully added!",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
    else:
        await message.answer(
            "❌ Channel already exists or error adding it.",
            reply_markup=admin_back_kb(),
        )


@router.callback_query(F.data.startswith("adm_rmchan_"))
async def cb_adm_rmchan(cb: CallbackQuery, db: Database, config: Config) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    channel_id = cb.data[len("adm_rmchan_"):]
    ok = await db.remove_channel(channel_id)
    if ok:
        await cb.answer("✅ Channel removed.", show_alert=False)
    else:
        await cb.answer("❌ Channel not found.", show_alert=True)
    # Refresh panel
    channels = await db.get_channels()
    count = len(channels)
    text = f"📡 <b>Force Join Channels ({count})</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for ch in channels:
        title = escape_html(ch.get("channel_title") or ch.get("channel_id"))
        uname = ch.get("channel_username") or "—"
        text += f"• {title} ({escape_html(uname)})\n"
    if not channels:
        text += "No channels.\n"
    await cb.message.edit_text(
        text, parse_mode="HTML", reply_markup=channels_kb(channels)
    )


@router.callback_query(F.data == "adm_tutorial")
async def cb_adm_tutorial(
    cb: CallbackQuery, config: Config, state: FSMContext
) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.upload_tutorial)
    await cb.message.edit_text(
        "🎬 <b>Upload Tutorial Video</b>\n\n"
        "Send a video that will be sent to users after a successful Premium claim.\n\n"
        "The video should show how to redeem a Telegram Premium code.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.upload_tutorial, F.video)
async def do_upload_tutorial(
    message: Message, db: Database, state: FSMContext, config: Config
) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    file_id = message.video.file_id
    await db.set_setting("tutorial_video_file_id", file_id)
    await message.answer(
        "✅ <b>Tutorial video saved!</b>\nIt will be sent to users after a successful claim.",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


@router.message(AdminStates.upload_tutorial)
async def do_upload_tutorial_invalid(
    message: Message, state: FSMContext, config: Config
) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await message.answer(
        "❌ Please send a <b>video</b> file.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


# ── Add Balance ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_add_balance")
async def cb_adm_add_balance(cb: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id, config):
        await cb.answer("Not authorized.", show_alert=True)
        return
    await cb.answer()
    await state.set_state(AdminStates.add_balance_id)
    await cb.message.edit_text(
        "💰 <b>Add Balance</b>\n\n"
        "Step 1/2: Send the <b>Telegram ID</b> of the user you want to add balance to.",
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
        await message.answer("❌ Send a valid Telegram ID (numbers only).", reply_markup=cancel_kb())
        return
    user = await db.get_user(tg_id)
    if not user:
        await message.answer(
            f"❌ User <code>{tg_id}</code> not found. They must start the bot first.",
            parse_mode="HTML",
            reply_markup=cancel_kb(),
        )
        return
    await state.update_data(target_tg_id=tg_id, target_user_id=user["id"],
                            target_name=user.get("first_name", "User"))
    await state.set_state(AdminStates.add_balance_amt)
    await message.answer(
        f"✅ User found: <b>{escape_html(user.get('first_name','User'))}</b> (<code>{tg_id}</code>)\n\n"
        "Step 2/2: How many <b>points</b> do you want to add? (send a number)",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(AdminStates.add_balance_amt)
async def do_add_balance_amt(
    message: Message, db: Database, bot: Bot, state: FSMContext, config: Config
) -> None:
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

    user_id   = data["target_user_id"]
    tg_id     = data["target_tg_id"]
    name      = data["target_name"]

    await db.add_to_wallet(user_id, amount, "other")
    wallet = await db.get_wallet(user_id)

    await message.answer(
        f"✅ <b>{format_number(amount)} points</b> have been added!\n\n"
        f"👤 User: <b>{escape_html(name)}</b> (<code>{tg_id}</code>)\n"
        f"💰 New Balance: <b>{format_number(wallet.get('balance', 0))} pts</b>",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )

    # Notify user
    try:
        await bot.send_message(
            tg_id,
            f"🎉 <b>Balance Added!</b>\n\n"
            f"Admin has added <b>{format_number(amount)} points</b> to your wallet!\n"
            f"💰 <b>New Balance:</b> {format_number(wallet.get('balance', 0))} pts",
            parse_mode="HTML",
        )
    except Exception:
        pass


# ── Cancel command ───────────────────────────────────────────────────────────────

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, config: Config) -> None:
    if not is_admin(message.from_user.id, config):
        return
    await state.clear()
    await message.answer(
        "❌ Action cancelled.",
        reply_markup=admin_main_kb(),
        parse_mode="HTML",
    )
