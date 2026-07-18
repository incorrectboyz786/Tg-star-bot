from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Tuple


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


def stars_tiers_kb(
    balance: int,
    tiers: List[Tuple[int, int, str]],
) -> InlineKeyboardMarkup:
    """Full-width tier selection buttons."""
    builder = InlineKeyboardBuilder()
    for stars, cost, icon in tiers:
        if balance >= cost:
            label = f"{icon}  {stars} Stars  —  {cost:,} pts  ✅"
            builder.row(
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"stars_tier_{stars}",
                    style="primary",
                )
            )
        else:
            needed = cost - balance
            label = f"🔒  {stars} Stars  —  {cost:,} pts  (need {needed:,})"
            builder.row(
                InlineKeyboardButton(
                    text=label,
                    callback_data="stars_locked",
                    style="primary",
                )
            )
    builder.row(
        InlineKeyboardButton(text="🏠 Back to Menu", callback_data="home", style="primary")
    )
    return builder.as_markup()


def confirm_tier_kb(stars: int, cost: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"✅  Confirm  —  {stars} Stars",
            callback_data=f"do_withdraw_{stars}_{cost}",
            style="primary",
        )
    )
    builder.row(
        InlineKeyboardButton(text="‹ Back to Packages", callback_data="get_stars", style="primary")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Back to Menu", callback_data="home")
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
            buttons.append(InlineKeyboardButton(text=f"📢  {label}", url=link, style="positive"))
        else:
            buttons.append(InlineKeyboardButton(text="⏳ Loading…", callback_data="noop"))
    builder.add(*buttons)
    builder.adjust(1)   # full-width channel buttons
    builder.row(
        InlineKeyboardButton(text="✅  Verify Joined", callback_data="verify_join", style="primary")
    )
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 Back to Menu", callback_data="home", style="primary")
    )
    return builder.as_markup()


def confirm_stars_kb() -> InlineKeyboardMarkup:
    """Legacy single-tier confirm (kept for compatibility)."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅  Yes, Withdraw!", callback_data="do_withdraw_stars", style="primary")
    )
    builder.row(
        InlineKeyboardButton(text="❌  Cancel", callback_data="home")
    )
    return builder.as_markup()
