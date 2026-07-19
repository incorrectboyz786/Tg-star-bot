import logging
import os
import random
import io
from PIL import Image, ImageDraw, ImageFont
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from database import Database
from config import Config
from keyboards.user_kb import main_menu_kb, force_join_kb, back_to_menu_kb

logger = logging.getLogger(__name__)
router = Router()

# ── Bot name cache ─────────────────────────────────────────────────────────────

_bot_name_cache: str | None = None


async def _get_bot_name(bot: Bot) -> str:
    """Fetch and cache the bot's display name from Telegram."""
    global _bot_name_cache
    if _bot_name_cache is None:
        try:
            info = await bot.get_me()
            _bot_name_cache = info.first_name or "Bot"
        except Exception:
            _bot_name_cache = "Bot"
    return _bot_name_cache


def _get_web_domain() -> str:
    """Return the public domain for fingerprint verify links.
    Priority: BOT_PUBLIC_URL > RAILWAY_PUBLIC_DOMAIN > REPLIT_DOMAINS > REPLIT_DEV_DOMAIN
    """
    custom = os.environ.get("BOT_PUBLIC_URL", "").strip().rstrip("/")
    if custom:
        return custom.replace("https://", "").replace("http://", "")
    railway = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if railway:
        return railway
    replit = os.environ.get("REPLIT_DOMAINS", "").split(",")[0].strip()
    if replit:
        return replit
    return os.environ.get("REPLIT_DEV_DOMAIN", "").strip()

MAX_CAPTCHA_ATTEMPTS = 3


# ── FSM ────────────────────────────────────────────────────────────────────────

class StartStates(StatesGroup):
    captcha = State()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _gen_captcha() -> tuple[str, int]:
    """Return (question_text, correct_answer)."""
    ops = [
        lambda a, b: (f"{a} + {b}", a + b),
        lambda a, b: (f"{a} × {b}", a * b),
        lambda a, b: (f"{a} - {b}", a - b),
    ]
    op = random.choice(ops)
    a, b = random.randint(2, 12), random.randint(2, 12)
    if op == ops[2] and b > a:   # avoid negative subtraction
        a, b = b, a
    q, ans = op(a, b)
    return q, ans


async def enrich_channels(bot: Bot, channels: list, db: Database) -> list[dict]:
    """
    Ensure every channel has an invite_link for the join button.

    - Public channels (@username): link = t.me/username, no admin needed.
    - Private channels (numeric ID + invite_link in DB): already stored, use directly.
    - Private channels (numeric ID, no invite_link yet): try to export/create one.
    """
    enriched = []
    for ch in channels:
        cid = ch.get("channel_id", "")

        # Already has invite link stored — use it directly
        if ch.get("invite_link"):
            enriched.append(ch)
            continue

        # Public channel — build link from username
        uname = ch.get("channel_username") or (cid if cid.startswith("@") else None)
        if uname:
            link = f"https://t.me/{uname.lstrip('@')}"
            enriched.append({**ch, "invite_link": link, "channel_username": uname})
            continue

        # Numeric ID private channel — try to get/create invite link via bot admin
        try:
            chat = await bot.get_chat(cid)
            title = chat.title or ch.get("channel_title") or cid

            if chat.invite_link:
                link = chat.invite_link
            else:
                try:
                    link = await bot.export_chat_invite_link(cid)
                except Exception:
                    invite = await bot.create_chat_invite_link(cid)
                    link = invite.invite_link

            await db.update_channel_invite_link(cid, link, title=title)
            enriched.append({**ch, "invite_link": link, "channel_title": title})
        except Exception as e:
            logger.warning("Could not get invite link for channel %s: %s", cid, e)
            enriched.append(ch)   # show without link (will show noop button)

    return enriched


async def check_force_join(bot: Bot, user_id: int, channels: list) -> list[dict]:
    """
    Returns list of channels the user has NOT joined.

    Uses channel_id (numeric or @username) for get_chat_member.
    Skips channels where bot is not admin (TelegramForbiddenError).
    Treats 'user not found' as not-joined.
    """
    not_joined = []
    for ch in channels:
        cid = ch.get("channel_id", "")

        # Skip if channel_id is an invite link URL (can't use for membership check)
        if cid.startswith("http") or "t.me/+" in cid:
            logger.warning(
                "Channel %s has invite link as ID — can't verify membership. "
                "Remove and re-add with numeric ID.",
                cid,
            )
            continue

        try:
            member = await bot.get_chat_member(chat_id=cid, user_id=user_id)
            if member.status in ("left", "kicked", "banned"):
                not_joined.append(ch)
        except TelegramForbiddenError as e:
            logger.warning(
                "⚠️  Channel %s: Bot not admin — skipping check. Make bot admin. Error: %s",
                cid, e,
            )
        except TelegramBadRequest as e:
            err_str = str(e).lower()
            if "user not found" in err_str or "participant_id_invalid" in err_str:
                not_joined.append(ch)
            else:
                logger.warning("⚠️  Channel %s check failed — skipping. Error: %s", cid, e)
        except Exception as e:
            logger.error("Unexpected error checking channel %s: %s — skipping", cid, e)

    return not_joined


async def _try_award_referral(user: dict, bot: Bot, db: Database) -> None:
    """Award referral points to referrer — only if user has a referrer and not yet awarded."""
    referrer_db_id = user.get("referrer_id")
    if not referrer_db_id:
        return
    reward = int(await db.get_setting("referral_reward", "100"))
    awarded = await db.add_referral_atomic(referrer_db_id, user["id"], reward)
    if awarded:
        try:
            ref_user_row = await db.get_user_by_id(referrer_db_id)
            if ref_user_row:
                await bot.send_message(
                    ref_user_row["telegram_id"],
                    f"🎉 <b>New Referral!</b>\n\n"
                    f"<b>{user.get('first_name', 'User')}</b> joined using your referral link "
                    f"and completed the channel join verification!\n"
                    f"<b>+{reward} points</b> have been added to your wallet! 💰",
                    parse_mode="HTML",
                )
        except Exception:
            pass


def generate_image_captcha(text: str) -> io.BytesIO:
    # Create an image with a light background
    width, height = 220, 80
    image = Image.new("RGB", (width, height), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    
    # Try loading DejaVuSans, fallback to default font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except Exception:
            font = ImageFont.load_default()
            
    # Draw background noise lines
    for _ in range(8):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=random.choice([(200, 200, 200), (180, 180, 180), (220, 220, 220)]), width=2)
        
    # Draw character by character with slight rotation/offset
    for i, char in enumerate(text):
        char_x = 20 + i * 35 + random.randint(-5, 5)
        char_y = 15 + random.randint(-8, 8)
        color = random.choice([
            (220, 50, 50),
            (50, 150, 50),
            (50, 50, 200),
            (150, 50, 150),
            (50, 150, 150),
            (50, 50, 50)
        ])
        draw.text((char_x, char_y), char, font=font, fill=color)
        
    # Draw foreground noise dots
    for _ in range(150):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(100, 100, 100))
        
    # Save image to BytesIO
    out = io.BytesIO()
    image.save(out, format="PNG")
    out.seek(0)
    return out


async def _send_captcha(target, state: FSMContext, attempts: int = 0) -> None:
    """Send a fresh image CAPTCHA. target = Message or CallbackQuery."""
    code = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
    await state.set_state(StartStates.captcha)
    await state.update_data(captcha_code=code, captcha_attempts=attempts)
    
    # Generate image
    image_data = generate_image_captcha(code)
    photo = BufferedInputFile(image_data.read(), filename="captcha.png")
    
    text = (
        "🔐 <b>Advanced Device Verification</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "To prevent bot abuse, please type the characters shown in the image below:\n\n"
        "<i>Type the 5 characters shown in the image below (Case-Insensitive).</i>"
    )
    
    if isinstance(target, CallbackQuery):
        try:
            await target.message.delete()
        except Exception:
            pass
        await target.message.answer_photo(photo, caption=text, parse_mode="HTML")
    else:
        await target.answer_photo(photo, caption=text, parse_mode="HTML")


# ── /start ─────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, db: Database, config: Config, bot: Bot, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user

    # Parse referral deep-link
    referrer_db_id = None
    args = message.text.split(maxsplit=1)[1] if " " in (message.text or "") else ""
    if args.startswith("ref_"):
        try:
            ref_tg_id = int(args[4:])
            if ref_tg_id != tg.id:
                ref_user = await db.get_user(ref_tg_id)
                if ref_user:
                    referrer_db_id = ref_user["id"]
        except ValueError:
            pass

    # Register / update
    user_db_id = await db.add_user(
        telegram_id=tg.id,
        username=tg.username,
        first_name=tg.first_name or "User",
        last_name=tg.last_name,
        referrer_id=referrer_db_id,
    )
    await db.update_user_info(tg.id, tg.username, tg.first_name or "User", tg.last_name)
    user = await db.get_user(tg.id)

    # ── Force Join — every /start ──────────────────────────────────────────
    channels = await db.get_channels()
    if channels:
        channels = await enrich_channels(bot, channels, db)
        if not user.get("force_join_done"):
            # Show join screen for ALL channels — bot may not be admin,
            # so don't filter here. Membership is only checked on "Verify Joined".
            try:
                import os
                from aiogram.types import FSInputFile
                _BOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                vid_path = os.path.join(_BOT_DIR, "vid.mp4")

                bot_display_name = await _get_bot_name(bot)
                caption_text = (
                    f"👋 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 {bot_display_name}\n\n"
                    "📢 𝙁𝙄𝙍𝙎𝙏 𝙅𝙊𝙄𝙉 𝘾𝙃𝘼𝙉𝙉𝙀𝙇.\n\n"
                    "𝙏𝙃𝙀𝙉 𝘾𝙇𝙄𝘾𝙆 𝙊𝙉 𝙑𝙀𝙍𝙄𝙁𝙄𝙀𝘿 𝙅𝙊𝙄𝙉."
                )

                if os.path.exists(vid_path):
                    await message.answer_video(
                        video=FSInputFile(vid_path),
                        caption=caption_text,
                        parse_mode="HTML",
                        reply_markup=force_join_kb(channels),
                    )
                else:
                    await message.answer(
                        text=caption_text,
                        parse_mode="HTML",
                        reply_markup=force_join_kb(channels),
                    )
            except TelegramForbiddenError:
                pass  # user blocked bot — nothing to do
            except Exception as e:
                logger.error("Failed to send start video: %s", e)
                try:
                    await message.answer(
                        text="👋 <b>Welcome!</b>\n\n"
                             "📢 <b>Pehle yeh channels join karo:</b>\n\n"
                             "Join karne ke baad <b>✅ Verify Joined</b> dabao.",
                        parse_mode="HTML",
                        reply_markup=force_join_kb(channels),
                    )
                except Exception:
                    pass
            return
        else:
            # Already passed force join — just ensure referral is awarded
            await _try_award_referral(user, bot, db)
    else:
        # No channels configured — award referral immediately if user is already verified,
        # otherwise it will be awarded in handle_captcha after verification.
        if user.get("device_verified"):
            await _try_award_referral(user, bot, db)

    # ── Device Verification (Web Fingerprint) ─────────────────────────────
    if not user.get("device_verified"):
        token = await db.create_device_token(user_db_id)
        domain = _get_web_domain()
        verify_url = f"https://{domain}/verify?t={token}" if domain else None

        builder = InlineKeyboardBuilder()
        if verify_url:
            builder.row(InlineKeyboardButton(
                text="🔍 Verify My Device", url=verify_url, style="primary"
            ))
        builder.row(InlineKeyboardButton(
            text="✅ I'm Verified", callback_data="check_fv", style="primary"
        ))

        await message.answer(
            "🔐 <b>Device Verification</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Tap <b>🔍 Verify My Device</b> to open the verification page.\n"
            "It checks your device silently (takes ~3 seconds).\n\n"
            "After the page shows <b>✅ Device Verified</b>, come back here\n"
            "and tap <b>✅ I'm Verified</b>.\n\n"
            "<i>⚠️ One device can only be linked to one account.</i>",
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
        )
        return

    # ── Main Menu ─────────────────────────────────────────────────────────
    await show_main_menu(message, tg.first_name or "User", db)




# ── noop (no link yet) ────────────────────────────────────────────────────────

@router.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery) -> None:
    await cb.answer("⏳ Fetching links, please /start again.", show_alert=True)


# ── Verify join ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "verify_join")
async def cb_verify_join(cb: CallbackQuery, db: Database, bot: Bot, state: FSMContext) -> None:
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        await cb.answer("Please /start first.", show_alert=True)
        return

    channels = await db.get_channels()
    channels = await enrich_channels(bot, channels, db)
    not_joined = await check_force_join(bot, tg.id, channels)

    if not_joined:
        await cb.answer("❌ You have not joined all channels yet!", show_alert=True)
        caption_text = (
            "📢 𝙁𝙄𝙍𝙎𝙏 𝙅𝙊𝙄𝙉 𝘾𝙃𝘼𝙉𝙉𝙀𝙇.\n\n"
            "𝙏𝙃𝙀𝙉 𝘾𝙇𝙄𝘾𝙆 𝙊𝙉 𝙑𝙀𝙍𝙄𝙁𝙄𝙀𝘿 𝙅𝙊𝙄𝙉."
        )
        if cb.message.video or cb.message.photo:
            try:
                await cb.message.edit_caption(
                    caption=caption_text,
                    parse_mode="HTML",
                    reply_markup=force_join_kb(not_joined)
                )
            except Exception:
                pass
        else:
            try:
                await cb.message.edit_text(
                    text=caption_text,
                    parse_mode="HTML",
                    reply_markup=force_join_kb(not_joined)
                )
            except Exception:
                pass
        return

    await db.set_force_join_done(user["id"])
    await cb.answer("✅ Channels verified!", show_alert=False)

    if not user.get("device_verified"):
        # Show web fingerprint verification next
        token = await db.create_device_token(user["id"])
        domain = _get_web_domain()
        verify_url = f"https://{domain}/verify?t={token}" if domain else None

        builder = InlineKeyboardBuilder()
        if verify_url:
            builder.row(InlineKeyboardButton(
                text="🔍 Verify My Device", url=verify_url, style="primary"
            ))
        builder.row(InlineKeyboardButton(
            text="✅ I'm Verified", callback_data="check_fv", style="primary"
        ))

        try:
            await cb.message.delete()
        except Exception:
            pass
        await cb.message.answer(
            "🔐 <b>Device Verification</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Tap <b>🔍 Verify My Device</b> to open the verification page.\n"
            "It checks your device silently (takes ~3 seconds).\n\n"
            "After the page shows <b>✅ Device Verified</b>, come back here\n"
            "and tap <b>✅ I'm Verified</b>.\n\n"
            "<i>⚠️ Ek phone = ek account. Multi-account allowed nahi.</i>",
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
        )
    else:
        # Already verified — award referral and go to menu
        await _try_award_referral(user, bot, db)
        if cb.message.video or cb.message.photo:
            try:
                await cb.message.delete()
            except Exception:
                pass
            await cb.message.answer(
                _home_text(tg.first_name or "User"),
                parse_mode="HTML",
                reply_markup=main_menu_kb(),
            )
        else:
            try:
                await cb.message.edit_text(
                    _home_text(tg.first_name or "User"),
                    parse_mode="HTML",
                    reply_markup=main_menu_kb(),
                )
            except Exception:
                pass


# ── Check device fingerprint verified ────────────────────────────────────────

@router.callback_query(F.data == "check_fv")
async def cb_check_fv(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    if not user:
        await cb.answer("Please /start first.", show_alert=True)
        return

    verified = await db.is_device_verified(user["id"])
    if verified:
        await _try_award_referral(user, cb.bot, db)
        try:
            await cb.message.edit_text(
                "✅ <b>Device Verified Successfully!</b>\n\n"
                "Your device is now linked to this account.\n"
                "Welcome to the bot! 🎉",
                parse_mode="HTML",
            )
        except Exception:
            pass
        await show_main_menu(cb.message, tg.first_name or "User", db)
    else:
        # Regenerate token so user can retry
        token = await db.create_device_token(user["id"])
        domain = _get_web_domain()
        verify_url = f"https://{domain}/verify?t={token}" if domain else None

        builder = InlineKeyboardBuilder()
        if verify_url:
            builder.row(InlineKeyboardButton(
                text="🔍 Verify My Device", url=verify_url, style="primary"
            ))
        builder.row(InlineKeyboardButton(
            text="✅ I'm Verified", callback_data="check_fv", style="primary"
        ))
        await cb.answer("❌ Device not verified yet!", show_alert=True)
        try:
            await cb.message.edit_reply_markup(reply_markup=builder.as_markup())
        except Exception:
            pass


# ── Home ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "home")
async def cb_home(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    tg = cb.from_user
    user = await db.get_user(tg.id)
    balance, streak = 0, 0
    if user:
        w = await db.get_wallet(user["id"])
        balance = w.get("balance", 0)
        sd = await db.get_streak(user["id"])
        streak = sd.get("streak", 0)
    await cb.message.edit_text(
        _home_text(tg.first_name or "User", balance, streak),
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


# ── Utils ─────────────────────────────────────────────────────────────────────

async def show_main_menu(message: Message, first_name: str, db: Database) -> None:
    tg = message.from_user
    user = await db.get_user(tg.id)
    balance, streak = 0, 0
    if user:
        w = await db.get_wallet(user["id"])
        balance = w.get("balance", 0)
        sd = await db.get_streak(user["id"])
        streak = sd.get("streak", 0)
    await message.answer(
        _home_text(first_name, balance, streak),
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


def _home_text(first_name: str, balance: int = 0, streak: int = 0) -> str:
    safe = first_name.replace("<", "&lt;").replace(">", "&gt;")
    fire = "🔥" if streak >= 7 else ("✨" if streak >= 3 else "⚡")
    streak_str = f"{fire} <b>{streak}-day streak!</b>" if streak > 1 else "⚡ Start your streak!"
    return (
        f"{'━' * 16}\n"
        f"  🏠  <b>Welcome back, {safe}!</b>\n"
        f"{'━' * 16}\n\n"
        f"💰 <b>Balance:</b>  <code>{balance:,} pts</code>\n"
        f"📅 <b>Daily Bonus:</b>  {streak_str}\n\n"
        f"{'─' * 16}\n"
        f"🌟 <b>What can you do?</b>\n"
        f"  👥  Refer friends → earn <b>+100 pts</b> each\n"
        f"  🎁  Daily bonus → free pts every 24h\n"
        f"  ⭐  Withdraw Telegram Stars with pts\n\n"
        f"Choose an option below 👇"
    )
