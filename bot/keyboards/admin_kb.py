from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict


def admin_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Statistics", callback_data="adm_stats"),
        InlineKeyboardButton(text="👥 Users", callback_data="adm_users"),
    )
    builder.row(
        InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast"),
        InlineKeyboardButton(text="🏆 Leaderboard", callback_data="adm_leaderboard"),
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Ban User", callback_data="adm_ban"),
        InlineKeyboardButton(text="✅ Unban User", callback_data="adm_unban"),
    )
    builder.row(
        InlineKeyboardButton(text="⏳ Pending Withdrawals", callback_data="adm_pending_withdrawals"),
        InlineKeyboardButton(text="📜 All Withdrawals", callback_data="adm_all_withdrawals"),
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Set Referral Reward", callback_data="adm_set_reward"),
        InlineKeyboardButton(text="⭐ Set Stars/Claim", callback_data="adm_set_stars"),
    )
    builder.row(
        InlineKeyboardButton(text="💎 Set Min Balance", callback_data="adm_set_min"),
        InlineKeyboardButton(text="💰 Add Balance", callback_data="adm_add_balance"),
    )
    builder.row(
        InlineKeyboardButton(text="📡 Force Join", callback_data="adm_channels"),
        InlineKeyboardButton(text="🔗 Set DM Link", callback_data="adm_set_dm_link"),
    )
    return builder.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="adm_panel"))
    return builder.as_markup()


def channels_kb(channels: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        title = ch.get("channel_title") or ch.get("channel_id")
        builder.row(
            InlineKeyboardButton(
                text=f"❌ Remove: {title}",
                callback_data=f"adm_rmchan_{ch['channel_id']}",
            )
        )
    builder.row(InlineKeyboardButton(text="➕ Add Channel", callback_data="adm_addchan"))
    builder.row(InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="adm_panel"))
    return builder.as_markup()


def cancel_kb(back_cb: str = "adm_panel") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data=back_cb))
    return builder.as_markup()


def withdrawal_action_kb(withdrawal_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Approve (Stars Sent)",
            callback_data=f"adm_approve_{withdrawal_id}",
        ),
        InlineKeyboardButton(
            text="❌ Reject & Refund",
            callback_data=f"adm_reject_{withdrawal_id}",
        ),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Admin Panel", callback_data="adm_panel"))
    return builder.as_markup()
