from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict


def admin_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Statistics", callback_data="adm_stats", style="primary"),
        InlineKeyboardButton(text="👥 Users", callback_data="adm_users", style="primary"),
    )
    builder.row(
        InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast", style="primary"),
        InlineKeyboardButton(text="🚫 Ban User", callback_data="adm_ban", style="primary"),
    )
    builder.row(
        InlineKeyboardButton(text="✅ Unban User", callback_data="adm_unban", style="primary"),
        InlineKeyboardButton(text="🏆 Leaderboard", callback_data="adm_leaderboard", style="primary"),
    )
    builder.row(
        InlineKeyboardButton(text="🎫 Add Codes", callback_data="adm_add_codes", style="primary"),
        InlineKeyboardButton(text="🗑 Delete Code", callback_data="adm_del_code", style="primary"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Delete ALL Codes", callback_data="adm_del_all_codes", style="primary"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Unused Codes", callback_data="adm_unused_codes", style="primary"),
        InlineKeyboardButton(text="✅ Used Codes", callback_data="adm_used_codes", style="primary"),
    )
    builder.row(
        InlineKeyboardButton(text="📜 Claim History", callback_data="adm_claim_history", style="primary"),
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Set Referral Reward", callback_data="adm_set_reward", style="primary"),
        InlineKeyboardButton(text="💎 Set Min Balance", callback_data="adm_set_min", style="primary"),
    )
    builder.row(
        InlineKeyboardButton(text="📡 Force Join", callback_data="adm_channels", style="primary"),
        InlineKeyboardButton(text="🎬 Upload Tutorial", callback_data="adm_tutorial", style="primary"),
    )
    builder.row(
        InlineKeyboardButton(text="💰 Add Balance", callback_data="adm_add_balance", style="primary"),
        InlineKeyboardButton(text="🔗 Set DM Link", callback_data="adm_set_dm_link", style="primary"),
    )
    return builder.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="adm_panel", style="danger")
    )
    return builder.as_markup()


def channels_kb(channels: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        title = ch.get("channel_title") or ch.get("channel_id")
        builder.row(
            InlineKeyboardButton(
                text=f"❌ Remove: {title}",
                callback_data=f"adm_rmchan_{ch['channel_id']}",
                style="danger",
            )
        )
    builder.row(
        InlineKeyboardButton(text="➕ Add Channel", callback_data="adm_addchan", style="primary")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="adm_panel", style="danger")
    )
    return builder.as_markup()


def cancel_kb(back_cb: str = "adm_panel") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data=back_cb, style="danger"))
    return builder.as_markup()
