import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardButton
from aiogram.client.session.middlewares.base import BaseRequestMiddleware

logger = logging.getLogger(__name__)

# ── Star Bot Premium Emoji IDs ──────────────────────────────────────────────
# Animated Telegram premium emoji IDs — star/reward bot themed

EMOJI_TO_ID = {
    # ── Stars (core theme) ───────────────────────────────────────────────────
    "⭐":  "5368324170671202286",   # animated gold star
    "🌟":  "5377367482674168462",   # glowing star
    "💫":  "5350114450535186500",   # dizzy / shooting star
    "✨":  "6253754970349243649",   # sparkles
    "🎇":  "5253652327734192243",   # fireworks / star burst
    "🎆":  "5039644681583985437",   # fireworks sparkle

    # ── Rewards & Ranks ──────────────────────────────────────────────────────
    "🏆":  "5274026806477857971",   # trophy
    "👑":  "5217822164362739968",   # crown
    "💎":  "6264791387032523779",   # diamond gem
    "🥇":  "6194737030165959506",   # gold medal
    "🥈":  "5348570868752595928",   # silver medal
    "🥉":  "5348570868752595928",   # bronze medal
    "🎖":  "5377445293933469655",   # military medal
    "🎗":  "5377445293933469655",   # reminder ribbon

    # ── Money & Points ───────────────────────────────────────────────────────
    "💰":  "6025976946083500432",   # money bag
    "💵":  "5409048419211682843",   # dollar bill
    "💳":  "5447453226498552490",   # credit card
    "🏦":  "5332455502917949981",   # bank
    "🏛":  "5188267429247071438",   # landmark
    "💸":  "6025976946083500432",   # flying money
    "🧾":  "5042290883949495533",   # receipt
    "💹":  "6025976946083500432",   # chart yen

    # ── Gifts & Bonuses ──────────────────────────────────────────────────────
    "🎁":  "5253652327734192243",   # gift box
    "🎀":  "5253652327734192243",   # ribbon bow
    "🎊":  "5039644681583985437",   # confetti
    "🎉":  "5039644681583985437",   # party popper
    "🥳":  "5039644681583985437",   # partying face

    # ── Energy & Fire ────────────────────────────────────────────────────────
    "🔥":  "5039644681583985437",   # fire / streak
    "⚡":  "5472250091332993630",   # lightning bolt
    "💥":  "5039644681583985437",   # collision/explosion
    "🚀":  "5472250091332993630",   # rocket

    # ── Status & Progress ────────────────────────────────────────────────────
    "✅":  "6113976436521963836",   # check mark
    "🟩":  "6113976436521963836",   # green square
    "❌":  "5893081007153746175",   # cross mark
    "🚫":  "5893081007153746175",   # no entry
    "⛔":  "5893081007153746175",   # no entry sign
    "⚠️": "6255910249362885846",   # warning
    "🔒":  "5291873529464122510",   # locked
    "🔐":  "5291873529464122510",   # locked with key
    "🔑":  "5454386656628991407",   # key
    "🛡":  "5291873529464122510",   # shield

    # ── Info & UI ────────────────────────────────────────────────────────────
    "📊":  "5042290883949495533",   # bar chart
    "📈":  "5042290883949495533",   # chart up
    "📉":  "5042290883949495533",   # chart down
    "📋":  "5042290883949495533",   # clipboard
    "📜":  "5226597108965993909",   # scroll
    "📅":  "5226597108965993909",   # calendar
    "📌":  "5039600026809009149",   # pushpin
    "📍":  "5039600026809009149",   # round pushpin
    "🔖":  "5039600026809009149",   # bookmark
    "💡":  "6253754970349243649",   # bulb
    "ℹ️": "5334544901428229844",   # info
    "❓":  "5226656353744862682",   # question
    "💬":  "5334544901428229844",   # speech bubble
    "📢":  "5472250091332993630",   # loudspeaker
    "📡":  "5447453226498552490",   # satellite

    # ── Users & Social ───────────────────────────────────────────────────────
    "👤":  "5042302287087666158",   # person
    "👥":  "5042302287087666158",   # people
    "👋":  "6253754970349243649",   # wave
    "🤝":  "5042302287087666158",   # handshake
    "👇":  "5039600026809009149",   # point down
    "🆔":  "5841276284155467413",   # id badge
    "📛":  "5042302287087666158",   # name badge
    "📧":  "5282843764451195532",   # email

    # ── Navigation ───────────────────────────────────────────────────────────
    "➡️": "5447181973544008180",   # right arrow
    "⬅️": "5447181973544008180",   # left arrow
    "⏩":  "5447181973544008180",   # fast forward
    "⏪":  "5447181973544008180",   # rewind
    "➕":  "6253754970349243649",   # plus
    "🔙":  "5447181973544008180",   # back
    "🔝":  "5447181973544008180",   # top

    # ── Time ─────────────────────────────────────────────────────────────────
    "⏰":  "5445350406215465190",   # alarm clock
    "⏳":  "5258419835922030550",   # hourglass flowing
    "⌛":  "5258419835922030550",   # hourglass done
    "🕐":  "5258419835922030550",   # clock 1
    "🕔":  "5258419835922030550",   # clock 4
    "💤":  "5258419835922030550",   # zzz sleep

    # ── Tech & Bot ───────────────────────────────────────────────────────────
    "🖥":  "5039579582764680065",   # desktop
    "📱":  "5039579582764680065",   # phone
    "🔗":  "5042101437237036298",   # link
    "🌐":  "5447453226498552490",   # globe
    "🌎":  "5224450179368767019",   # earth americas
    "🌍":  "5447410659077661506",   # earth europe
    "⚙️": "5445059250382469069",   # gear
    "🔧":  "5445059250382469069",   # wrench
    "🤖":  "5895254947800291880",   # robot
    "👾":  "5895254947800291880",   # alien monster

    # ── Misc ─────────────────────────────────────────────────────────────────
    "🗑":  "5893081007153746175",   # trash
    "🚬":  "5429495925284296642",   # cigarette
    "💠":  "5445146945024720188",   # diamond shape
    "🔹":  "5445146945024720188",   # small blue diamond
    "🎫":  "6264791387032523779",   # ticket
    "🃏":  "6028206863038811654",   # joker
    "🎬":  "5039579582764680065",   # clapper
    "📤":  "5042101437237036298",   # outbox
    "🧮":  "5445350406215465190",   # abacus
    "🎯":  "5377445293933469655",   # target
    "⬜":  "5893081007153746175",   # white square

    # ── Number emojis (used in help/steps) ───────────────────────────────────
    "1️⃣": "5447181973544008180",
    "2️⃣": "5447181973544008180",
    "3️⃣": "5447181973544008180",
}


def replace_emojis_with_premium(text: str) -> str:
    if not isinstance(text, str):
        return text
    if "<tg-emoji" in text:
        return text
    for emoji_char, emoji_id in EMOJI_TO_ID.items():
        if emoji_char in text:
            text = text.replace(
                emoji_char,
                f'<tg-emoji emoji-id="{emoji_id}">{emoji_char}</tg-emoji>',
            )
    return text


_orig_init = InlineKeyboardButton.__init__


def new_init(self, *args, **kwargs):
    text = kwargs.get("text")
    if not text and args:
        text = args[0]
    if text and isinstance(text, str):
        found_emoji_id = None
        found_emoji_char = None
        for emoji_char, emoji_id in EMOJI_TO_ID.items():
            if emoji_char in text:
                found_emoji_id = emoji_id
                found_emoji_char = emoji_char
                break
        if found_emoji_id and not kwargs.get("icon_custom_emoji_id"):
            kwargs["icon_custom_emoji_id"] = found_emoji_id
            new_text = text.replace(found_emoji_char, "").strip()
            if not new_text:
                new_text = " "
            if "text" in kwargs:
                kwargs["text"] = new_text
            elif args:
                args = (new_text,) + args[1:]
    _orig_init(self, *args, **kwargs)


InlineKeyboardButton.__init__ = new_init


class PremiumEmojiRequestMiddleware(BaseRequestMiddleware):
    async def __call__(self, make_request, bot, method):
        if method.__class__.__name__ != "AnswerCallbackQuery":
            if hasattr(method, "text") and method.text:
                method.text = replace_emojis_with_premium(method.text)
            if hasattr(method, "caption") and method.caption:
                method.caption = replace_emojis_with_premium(method.caption)
        return await make_request(bot, method)
