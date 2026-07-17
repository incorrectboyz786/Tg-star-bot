import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardButton
from aiogram.client.session.middlewares.base import BaseRequestMiddleware

logger = logging.getLogger(__name__)

EMOJI_TO_ID = {
    "⚡": "5472250091332993630",
    "💰": "6025976946083500432",
    "💳": "5447453226498552490",
    "📊": "5042290883949495533",
    "👛": "5444960062407732826",
    "🏦": "5332455502917949981",
    "🏛": "5188267429247071438",
    "🌎": "5224450179368767019",
    "⏰": "5445350406215465190",
    "👑": "5217822164362739968",
    "✅": "6113976436521963836",
    "📧": "5282843764451195532",
    "💠": "5445146945024720188",
    "👤": "5042302287087666158",
    "👥": "5042302287087666158",
    "🆔": "5841276284155467413",
    "🎖": "5377445293933469655",
    "🔒": "5291873529464122510",
    "🔐": "5291873529464122510",
    "📅": "5226597108965993909",
    "🌐": "5447453226498552490",
    "📌": "5039600026809009149",
    "🥈": "5348570868752595928",
    "🥇": "6194737030165959506",
    "🏆": "5274026806477857971",
    "💎": "6264791387032523779",
    "⭐": "6264791387032523779",
    "❌": "5893081007153746175",
    "⚠️": "6255910249362885846",
    "🚫": "5893081007153746175",
    "🗑": "5893081007153746175",
    "🕔": "5258419835922030550",
    "🚬": "5429495925284296642",
    "🔥": "5039644681583985437",
    "👾": "5895254947800291880",
    "🔑": "5454386656628991407",
    "🎫": "6264791387032523779",
    "🃏": "6028206863038811654",
    "🖥": "5039579582764680065",
    "🔗": "5042101437237036298",
    "ℹ️": "5334544901428229844",
    "🌍": "5447410659077661506",
    "🇺🇸": "6034969533859499947",
    "💵": "5409048419211682843",
    "⚙️": "5445059250382469069",
    "✨": "6253754970349243649",
    "🏠": "5980995951160987855",
    "🎁": "5253652327734192243",
    "❓": "5226656353744862682",
    "📢": "5472250091332993630",
    "➡️": "5447181973544008180",
    "⏩": "5447181973544008180",
    "📋": "5042290883949495533",
    "📜": "5226597108965993909",
    "📡": "5447453226498552490",
    "🎬": "5039579582764680065",
    "⬅️": "5447181973544008180",
    "➕": "6253754970349243649",
    "👋": "6253754970349243649",
    "🧮": "5445350406215465190",
    "🎉": "5039644681583985437",
    "👇": "5039600026809009149",
    "🔹": "5445146945024720188",
    "💬": "5334544901428229844",
    "🕐": "5258419835922030550",
    "💡": "6253754970349243649",
    "📛": "5042302287087666158",
    "🔖": "5039600026809009149",
    "💤": "5258419835922030550",
    "📤": "5042101437237036298",
    "⏳": "5258419835922030550",
    "🟩": "6113976436521963836",
    "⬜": "5893081007153746175"
}

def replace_emojis_with_premium(text: str) -> str:
    if not isinstance(text, str):
        return text
    if "<tg-emoji" in text:
        return text
    for emoji_char, emoji_id in EMOJI_TO_ID.items():
        if emoji_char in text:
            text = text.replace(emoji_char, f'<tg-emoji emoji-id="{emoji_id}">{emoji_char}</tg-emoji>')
    return text

_orig_init = InlineKeyboardButton.__init__

def new_init(self, *args, **kwargs):
    text = kwargs.get('text')
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
        if found_emoji_id and not kwargs.get('icon_custom_emoji_id'):
            kwargs['icon_custom_emoji_id'] = found_emoji_id
            new_text = text.replace(found_emoji_char, '').strip()
            if not new_text:
                new_text = " "
            if 'text' in kwargs:
                kwargs['text'] = new_text
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
