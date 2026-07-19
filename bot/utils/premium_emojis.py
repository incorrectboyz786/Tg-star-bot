import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardButton
from aiogram.client.session.middlewares.base import BaseRequestMiddleware

logger = logging.getLogger(__name__)

# ── Verified Telegram Premium Emoji IDs ──────────────────────────────────────
# Only IDs confirmed working are used here.
# New emoji chars are mapped to the nearest verified ID.

EMOJI_TO_ID = {
    # ── Stars & Sparkles (core theme) ────────────────────────────────────────
    "⭐":  "6264791387032523779",   # star (verified)
    "🌟":  "6264791387032523779",   # glowing star → same verified star ID
    "💫":  "6253754970349243649",   # shooting star → sparkles (verified)
    "✨":  "6253754970349243649",   # sparkles (verified)
    "💎":  "6264791387032523779",   # diamond (verified)
    "🎫":  "6264791387032523779",   # ticket (verified)

    # ── Rewards & Ranks ──────────────────────────────────────────────────────
    "🏆":  "5274026806477857971",   # trophy (verified)
    "👑":  "5217822164362739968",   # crown (verified)
    "🥇":  "6194737030165959506",   # gold medal (verified)
    "🥈":  "5348570868752595928",   # silver medal (verified)
    "🥉":  "5348570868752595928",   # bronze → same as silver (verified)
    "🎖":  "5377445293933469655",   # medal (verified)
    "🎯":  "5377445293933469655",   # target → same verified ID

    # ── Money & Points ───────────────────────────────────────────────────────
    "💰":  "6025976946083500432",   # money bag (verified)
    "💵":  "5409048419211682843",   # dollar bill (verified)
    "💸":  "6025976946083500432",   # flying money → same as 💰
    "💳":  "5447453226498552490",   # card (verified)
    "🏦":  "5332455502917949981",   # bank (verified)
    "🏛":  "5188267429247071438",   # landmark (verified)
    "👛":  "5444960062407732826",   # purse (verified)

    # ── Gifts & Bonuses ──────────────────────────────────────────────────────
    "🎁":  "5253652327734192243",   # gift (verified)
    "🎉":  "5039644681583985437",   # party (verified)
    "🎊":  "5039644681583985437",   # confetti → same as 🎉
    "🥳":  "5039644681583985437",   # partying → same as 🎉

    # ── Energy & Streaks ─────────────────────────────────────────────────────
    "🔥":  "5039644681583985437",   # fire (verified)
    "⚡":  "5472250091332993630",   # lightning (verified)
    "🚀":  "5472250091332993630",   # rocket → same as ⚡
    "💥":  "5039644681583985437",   # boom → same as 🔥

    # ── Status ───────────────────────────────────────────────────────────────
    "✅":  "6113976436521963836",   # check (verified)
    "🟩":  "6113976436521963836",   # green box → same as ✅
    "❌":  "5893081007153746175",   # cross (verified)
    "🚫":  "5893081007153746175",   # no (verified)
    "⛔":  "5893081007153746175",   # stop → same
    "🗑":  "5893081007153746175",   # trash → same
    "⬜":  "5893081007153746175",   # white sq → same
    "⚠️": "6255910249362885846",   # warning (verified)
    "🔒":  "5291873529464122510",   # lock (verified)
    "🔐":  "5291873529464122510",   # locked key (verified)
    "🛡":  "5291873529464122510",   # shield → same as 🔒
    "🔑":  "5454386656628991407",   # key (verified)

    # ── Info & UI ────────────────────────────────────────────────────────────
    "📊":  "5042290883949495533",   # chart (verified)
    "📈":  "5042290883949495533",   # chart up → same
    "📋":  "5042290883949495533",   # clipboard → same
    "🧾":  "5042290883949495533",   # receipt → same
    "📅":  "5226597108965993909",   # calendar (verified)
    "📜":  "5226597108965993909",   # scroll → same
    "📌":  "5039600026809009149",   # pin (verified)
    "🔖":  "5039600026809009149",   # bookmark → same
    "👇":  "5039600026809009149",   # down → same
    "💡":  "6253754970349243649",   # bulb → sparkles
    "➕":  "6253754970349243649",   # plus → sparkles
    "👋":  "6253754970349243649",   # wave → sparkles
    "ℹ️": "5334544901428229844",   # info (verified)
    "💬":  "5334544901428229844",   # chat → same
    "❓":  "5226656353744862682",   # question (verified)
    "📢":  "5472250091332993630",   # speaker → same as ⚡
    "📡":  "5447453226498552490",   # satellite → same as 💳
    "🌐":  "5447453226498552490",   # globe → same
    "💠":  "5445146945024720188",   # diamond shape (verified)
    "🔹":  "5445146945024720188",   # blue diamond → same
    "🃏":  "6028206863038811654",   # joker (verified)

    # ── Users & Social ───────────────────────────────────────────────────────
    "👤":  "5042302287087666158",   # person (verified)
    "👥":  "5042302287087666158",   # people (verified)
    "🤝":  "5042302287087666158",   # handshake → same
    "📛":  "5042302287087666158",   # name badge → same
    "🆔":  "5841276284155467413",   # id (verified)
    "📧":  "5282843764451195532",   # email (verified)

    # ── Navigation ───────────────────────────────────────────────────────────
    "➡️": "5447181973544008180",   # right (verified)
    "⬅️": "5447181973544008180",   # left (verified)
    "⏩":  "5447181973544008180",   # forward → same
    "🔙":  "5447181973544008180",   # back → same
    "🔝":  "5447181973544008180",   # top → same

    # ── Time ─────────────────────────────────────────────────────────────────
    "⏰":  "5445350406215465190",   # alarm (verified)
    "🧮":  "5445350406215465190",   # abacus → same
    "⏳":  "5258419835922030550",   # hourglass (verified)
    "⌛":  "5258419835922030550",   # hourglass done → same
    "🕐":  "5258419835922030550",   # clock → same
    "🕔":  "5258419835922030550",   # clock 4 → same
    "💤":  "5258419835922030550",   # sleep → same

    # ── Tech ─────────────────────────────────────────────────────────────────
    "🖥":  "5039579582764680065",   # desktop (verified)
    "📱":  "5039579582764680065",   # phone → same
    "🎬":  "5039579582764680065",   # clapper → same
    "🔗":  "5042101437237036298",   # link (verified)
    "📤":  "5042101437237036298",   # outbox → same
    "🌎":  "5224450179368767019",   # earth (verified)
    "🌍":  "5447410659077661506",   # earth EU (verified)
    "🇺🇸": "6034969533859499947",  # flag US (verified)
    "⚙️": "5445059250382469069",   # gear (verified)
    "🔧":  "5445059250382469069",   # wrench → same
    "👾":  "5895254947800291880",   # alien (verified)
    "🤖":  "5895254947800291880",   # robot → same

    # ── Misc ─────────────────────────────────────────────────────────────────
    "🏠":  "5980995951160987855",   # home (verified)
    "🚬":  "5429495925284296642",   # cigarette (verified)
    "📣":  "5472250091332993630",   # megaphone → same as ⚡
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
