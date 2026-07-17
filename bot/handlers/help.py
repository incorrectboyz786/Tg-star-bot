import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

logger = logging.getLogger(__name__)
router = Router()

HELP_PAGES = {
    "help": (
        "❓ <b>Help &amp; Guide</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👋 Welcome! Here's everything you need to know:\n\n"
        "📌 <b>Sections:</b>\n"
        "  ├ 🎯  How it works\n"
        "  ├ 💰  How to earn points\n"
        "  ├ ⭐  How to get Stars\n"
        "  ├ 🏆  Rank system\n"
        "  └ ❓  FAQ\n\n"
        "Tap a button below to learn more! 👇",
        "help_earn", "help_stars", "help_ranks", "help_faq",
    ),
    "help_earn": (
        "💰 <b>How to Earn Points</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "There are 2 ways to earn points:\n\n"
        "👥 <b>1. Refer Friends</b>\n"
        "   Share your referral link from the\n"
        "   <b>Refer &amp; Earn</b> section.\n"
        "   You earn <b>+100 pts</b> for every friend\n"
        "   who joins and verifies!\n\n"
        "🎁 <b>2. Daily Bonus</b>\n"
        "   Claim your free daily bonus every 24h.\n"
        "   Keep your streak alive for <b>bigger rewards:</b>\n\n"
        "   ⚡ Day 1-2:   Base bonus\n"
        "   ✨ Day 3-4:   +20% bonus\n"
        "   ✨ Day 5-6:   +50% bonus\n"
        "   🔥 Day 7:     <b>2× bonus!</b>\n"
        "   🔥🔥 Day 14:  <b>3× bonus!</b>\n"
        "   🔥🔥🔥 Day 30: <b>5× bonus!</b>",
        "help", "help_stars", "help_ranks", "help_faq",
    ),
    "help_stars": (
        "⭐ <b>How to Get Telegram Stars</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Once you have enough points, you can\n"
        "withdraw <b>Telegram Stars</b> directly!\n\n"
        "📦 <b>Available Packages:</b>\n\n"
        "  ⭐  15 Stars   →  300 pts\n"
        "  🌟  50 Stars   →  900 pts\n"
        "  💫  100 Stars  →  1,700 pts\n"
        "  🌠  250 Stars  →  4,000 pts\n\n"
        "📋 <b>How it works:</b>\n"
        "  1️⃣  Tap <b>⭐ Get Stars</b>\n"
        "  2️⃣  Choose your package\n"
        "  3️⃣  Confirm the withdrawal\n"
        "  4️⃣  Admin sends Stars to your account\n"
        "  5️⃣  Done! Check <b>My Withdrawals</b>\n\n"
        "⏱ <i>Processing time: Usually within 24h.</i>",
        "help", "help_earn", "help_ranks", "help_faq",
    ),
    "help_ranks": (
        "🏆 <b>Rank System</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Earn points to level up your rank!\n"
        "Higher rank = more street cred 😎\n\n"
        "  🌱  <b>Newcomer</b>   →  0 pts\n"
        "  🥉  <b>Bronze</b>     →  500 pts\n"
        "  🥈  <b>Silver</b>     →  2,000 pts\n"
        "  🥇  <b>Gold</b>       →  5,000 pts\n"
        "  💎  <b>Platinum</b>   →  10,000 pts\n"
        "  👑  <b>Diamond</b>    →  25,000 pts\n"
        "  🌟  <b>Legend</b>     →  50,000 pts\n\n"
        "Your rank is shown on your <b>Profile</b> page.\n"
        "Rank up by referring friends &amp; daily bonus!",
        "help", "help_earn", "help_stars", "help_faq",
    ),
    "help_faq": (
        "❓ <b>Frequently Asked Questions</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Q: When will I receive my Stars?</b>\n"
        "A: Usually within 24 hours of approval.\n\n"
        "<b>Q: What if my withdrawal is rejected?</b>\n"
        "A: Points are automatically refunded.\n\n"
        "<b>Q: Can I refer unlimited people?</b>\n"
        "A: Yes! No referral limit.\n\n"
        "<b>Q: Does my streak reset if I miss a day?</b>\n"
        "A: Yes, streak resets to 1 if you miss\n"
        "   your daily bonus for 24+ hours.\n\n"
        "<b>Q: Is this bot safe?</b>\n"
        "A: Yes! Points are stored securely and\n"
        "   Stars are sent directly by an admin.\n\n"
        "<b>Q: Where do I get support?</b>\n"
        "A: Contact the bot admin for help.",
        "help", "help_earn", "help_stars", "help_ranks",
    ),
}

NAV_LABELS = {
    "help":       "📖 Overview",
    "help_earn":  "💰 Earn Points",
    "help_stars": "⭐ Get Stars",
    "help_ranks": "🏆 Ranks",
    "help_faq":   "❓ FAQ",
}


def _help_kb(page_key: str, nav_keys):
    builder = InlineKeyboardBuilder()
    nav = [k for k in nav_keys if k != page_key]
    for key in nav:
        builder.row(InlineKeyboardButton(
            text=NAV_LABELS.get(key, key),
            callback_data=key,
            style="primary",
        ))
    builder.row(InlineKeyboardButton(text="🏠 Back to Menu", callback_data="home", style="primary"))
    return builder.as_markup()


def _register_page(key: str, data: tuple):
    text = data[0]
    nav_keys = data[1:]

    @router.callback_query(F.data == key)
    async def handler(cb: CallbackQuery, _text=text, _key=key, _nav=nav_keys):
        await cb.answer()
        try:
            await cb.message.edit_text(_text, parse_mode="HTML", reply_markup=_help_kb(_key, _nav))
        except Exception:
            await cb.message.answer(_text, parse_mode="HTML", reply_markup=_help_kb(_key, _nav))

    return handler


# Register all help pages dynamically
for _key, _data in HELP_PAGES.items():
    _register_page(_key, _data)
