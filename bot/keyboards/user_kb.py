from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 Home", callback_data="home", style="primary"),
        InlineKeyboardButton(text="👤 Profile", callback_data="profile", style="primary"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Refer & Earn", callback_data="refer", style="primary"),
        InlineKeyboardButton(text="💰 Wallet", callback_data="wallet", style="primary"),
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Daily Bonus", callback_data="daily_bonus", style="primary"),
        InlineKeyboardButton(text="⭐ Get Stars", callback_data="get_stars", style="primary"),
    )
    builder.row(
        InlineKeyboardButton(text="📜 My Withdrawals", callback_data="my_withdrawals", style="primary"),
        InlineKeyboardButton(text="❓ Help", callback_data="help", style="primary"),
    )
    return builder.as_markup()


def force_join_kb(channels: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = []
    for ch in channels:
        label = ch.get("channel_title") or ch.get("channel_username") or "Channel"
        uname = ch.get("channel_username")
        link = (
            ch.get("invite_link")
            or (f"https://t.me/{uname.lstrip('@')}" if uname else None)
        )
        if link:
            buttons.append(InlineKeyboardButton(text=f"📢 {label}", url=link, style="primary"))
        else:
            buttons.append(InlineKeyboardButton(text="⏳ Loading…", callback_data="noop"))
    builder.add(*buttons)
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="✅ Verify Joined", callback_data="verify_join", style="success"))
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Back to Menu", callback_data="home", style="primary"))
    return builder.as_markup()


def confirm_stars_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yes, Withdraw!", callback_data="do_withdraw_stars", style="success"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="home", style="danger"),
    )
    return builder.as_markup()
