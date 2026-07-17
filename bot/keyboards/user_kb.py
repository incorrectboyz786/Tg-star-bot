from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 Home", callback_data="home"),
        InlineKeyboardButton(text="👤 Profile", callback_data="profile"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Refer & Earn", callback_data="refer"),
        InlineKeyboardButton(text="💰 Wallet", callback_data="wallet"),
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Daily Bonus", callback_data="daily_bonus"),
        InlineKeyboardButton(text="⭐ Get Stars", callback_data="get_stars"),
    )
    builder.row(
        InlineKeyboardButton(text="📜 My Withdrawals", callback_data="my_withdrawals"),
        InlineKeyboardButton(text="❓ Help", callback_data="help"),
    )
    return builder.as_markup()


def force_join_kb(channels: List[Dict], all_joined: bool = False) -> InlineKeyboardMarkup:
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
            buttons.append(InlineKeyboardButton(text=f"📢 {label}", url=link))
        else:
            buttons.append(InlineKeyboardButton(text="⏳ Loading…", callback_data="noop"))
    builder.add(*buttons)
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="✅ Verify Joined", callback_data="verify_join")
    )
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Back to Menu", callback_data="home"))
    return builder.as_markup()


def confirm_stars_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yes, Withdraw!", callback_data="do_withdraw_stars"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="home"),
    )
    return builder.as_markup()
