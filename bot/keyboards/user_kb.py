from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Optional


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
        InlineKeyboardButton(text="⭐ Get Premium", callback_data="get_premium", style="primary"),
    )
    builder.row(
        InlineKeyboardButton(text="❓ Help", callback_data="help", style="primary"),
    )
    return builder.as_markup()


def force_join_kb(channels: List[Dict], all_joined: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = []
    for ch in channels:
        label = ch.get("channel_title") or ch.get("channel_username") or "Channel"
        # Build a usable link — prefer invite_link, then @username, skip if neither exists
        uname = ch.get("channel_username")
        link = (
            ch.get("invite_link")
            or (f"https://t.me/{uname.lstrip('@')}" if uname else None)
        )
        if link:
            buttons.append(InlineKeyboardButton(text="📢 Must Join", url=link, style="primary"))
        else:
            buttons.append(InlineKeyboardButton(text="⏳ Must Join (loading…)", callback_data="noop", style="primary"))
    
    # Lay out channel buttons side by side (2 per row)
    builder.add(*buttons)
    builder.adjust(2)
    
    # Add verify button at the bottom in its own row
    builder.row(
        InlineKeyboardButton(text="✅ Verify Joined", callback_data="verify_join", style="primary")
    )
    return builder.as_markup()


def device_verify_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔐 Verify My Device", callback_data="verify_device", style="success"
        )
    )
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Back to Menu", callback_data="home", style="danger"))
    return builder.as_markup()


def claim_premium_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⭐ Claim Premium Now", callback_data="confirm_claim", style="primary")
    )
    builder.row(InlineKeyboardButton(text="🏠 Back to Menu", callback_data="home", style="danger"))
    return builder.as_markup()


def confirm_claim_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yes, Claim!", callback_data="do_claim", style="primary"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="home", style="danger"),
    )
    return builder.as_markup()


def sliding_captcha_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Controls
    builder.row(
        InlineKeyboardButton(text="⬅️ Move Left", callback_data="captcha_left"),
        InlineKeyboardButton(text="➡️ Move Right", callback_data="captcha_right")
    )
    
    # Verify Button
    builder.row(
        InlineKeyboardButton(text="✅ Verify & Unlock", callback_data="captcha_verify")
    )
    
    return builder.as_markup()

