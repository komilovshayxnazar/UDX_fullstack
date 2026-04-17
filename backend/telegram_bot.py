"""
Telegram Bot for UDX OTP Delivery.

Flow (asosiy — telefon raqami orqali):
  1. Foydalanuvchi /start yuboradi.
  2. Bot "Telefon raqamni ulashish" tugmasini ko'rsatadi.
  3. Foydalanuvchi tugmani bosadi — Telegram telefon raqamini yuboradi.
  4. Bot phone_hash → chat_id ni saqlaydi.
  5. Ilova OTP so'raganda, backend send_otp_by_phone_hash() chaqiradi.

Flow (token — ilovadan deeplink orqali):
  1. Ilova /start TOKEN deeplink ochadi.
  2. Bot tokenni auth.py ga xabar qiladi — u OTP yuboradi.
"""

import os
import json
import logging
from pathlib import Path
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logger = logging.getLogger(__name__)

# ── Disk-persisted storlar ───────────────────────────────────────────────────

_USERNAME_STORE_PATH    = Path(__file__).parent / "telegram_chat_ids.json"
_PHONE_HASH_STORE_PATH  = Path(__file__).parent / "telegram_phone_chat_ids.json"


def _load_store(path: Path) -> dict[str, int]:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _save_store(store: dict[str, int], path: Path) -> None:
    try:
        path.write_text(json.dumps(store))
    except Exception as e:
        logger.error(f"[TelegramBot] Failed to persist store {path.name}: {e}")


# { telegram_username (lowercase) -> chat_id }  — eski flow uchun
_username_to_chat_id: dict[str, int] = _load_store(_USERNAME_STORE_PATH)

# { phone_hash -> chat_id }  — yangi asosiy flow
_phone_hash_to_chat_id: dict[str, int] = _load_store(_PHONE_HASH_STORE_PATH)

# { token -> chat_id }  — ilovadan deeplink orqali kelgan tokenlar
_token_to_chat_id: dict[str, int] = {}

# Global Application reference (set when bot starts)
_app: Application | None = None


def _phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Telefon raqamni so'rash uchun bir martalik tugma."""
    button = KeyboardButton("📱 Telefon raqamni ulashish", request_contact=True)
    return ReplyKeyboardMarkup(
        [[button]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )


async def _start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /start [TOKEN]

    TOKEN bilan → ilovadan kelgan deeplink, OTP yuboriladi.
    TOKEN siz  → asosiy flow: telefon raqam so'raladi.
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    args = context.args

    if args:
        # Ilova deeplink flow: /start TOKEN
        token = args[0].strip()
        _token_to_chat_id[token] = chat_id
        logger.info(f"[TelegramBot] Token {token!r} → chat_id={chat_id}")
        await update.message.reply_text(
            "✅ Tayyor! Tasdiqlash kodi hozir yuborilmoqda...\n\n"
            "Kodni olgach, ilovaga qaytib kiriting 📱",
            reply_markup=ReplyKeyboardRemove(),
        )
        if _on_token_arrived:
            import asyncio
            asyncio.create_task(_on_token_arrived(token, chat_id))
    else:
        # Asosiy flow: telefon raqam so'rash
        name = user.first_name if user else "Foydalanuvchi"
        await update.message.reply_text(
            f"Assalomu alaykum, {name}! 👋\n\n"
            "UDX — qishloq xo'jaligi mahsulotlari bozori.\n\n"
            "Ro'yxatdan o'tish yoki kirish uchun telefon raqamingizni ulashing 👇",
            reply_markup=_phone_request_keyboard(),
        )


async def _contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Foydalanuvchi "Telefon raqamni ulashish" tugmasini bosganda chaqiriladi.
    phone_hash → chat_id ni saqlaydi.
    """
    from core.encryption import hmac_hash

    contact = update.message.contact
    chat_id = update.effective_chat.id

    if not contact or not contact.phone_number:
        await update.message.reply_text(
            "Telefon raqam olinmadi. Iltimos, tugmani bosib ulashing.",
            reply_markup=_phone_request_keyboard(),
        )
        return

    # Raqamni standart formatga keltirish
    phone = contact.phone_number.strip()
    if not phone.startswith("+"):
        phone = "+" + phone

    phone_hash = hmac_hash(phone)
    _phone_hash_to_chat_id[phone_hash] = chat_id
    _save_store(_phone_hash_to_chat_id, _PHONE_HASH_STORE_PATH)

    logger.info(f"[TelegramBot] Phone registered: hash=...{phone_hash[-6:]} chat_id={chat_id}")

    await update.message.reply_text(
        "✅ Telefon raqam saqlandi!\n\n"
        "Endi UDX ilovasidan ro'yxatdan o'ting — "
        "tasdiqlash kodi shu yerga yuboriladi 🚀",
        reply_markup=ReplyKeyboardRemove(),
    )

# Callback: set by auth.py to handle token arrival
_on_token_arrived = None

def set_token_callback(callback) -> None:
    global _on_token_arrived
    _on_token_arrived = callback


async def send_otp_to_chat(chat_id: int, otp_code: str) -> bool:
    """Send OTP directly to a chat_id (phone-based flow)."""
    if not _app:
        return False
    try:
        await _app.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🔐 UDX tasdiqlash kodingiz:\n\n"
                f"  `{otp_code}`\n\n"
                f"Kod 5 daqiqa davomida amal qiladi. Hech kimga bermang."
            ),
            parse_mode="Markdown"
        )
        logger.info(f"[TelegramBot] OTP sent to chat_id={chat_id}")
        return True
    except Exception as e:
        logger.error(f"[TelegramBot] Failed to send OTP to chat_id={chat_id}: {e}")
        return False


def get_chat_id_by_token(token: str) -> int | None:
    """Return chat_id for a given token, or None."""
    return _token_to_chat_id.get(token)


def get_chat_id_by_phone_hash(phone_hash: str) -> int | None:
    """Return chat_id for a given phone_hash (registered via contact share), or None."""
    return _phone_hash_to_chat_id.get(phone_hash)


async def send_otp_by_phone_hash(phone_hash: str, otp_code: str) -> bool:
    """Send OTP to a user who registered their phone via the bot's contact button."""
    chat_id = _phone_hash_to_chat_id.get(phone_hash)
    if not chat_id:
        logger.warning(f"[TelegramBot] No chat_id for phone_hash ...{phone_hash[-6:]}")
        return False
    return await send_otp_to_chat(chat_id, otp_code)


async def send_otp(telegram_username: str, otp_code: str) -> bool:
    """
    Send an OTP code to a Telegram user by username.
    Returns True on success, False if user not found or send failed.
    """
    if not _app:
        logger.error("[TelegramBot] Bot not initialized yet.")
        return False

    username = telegram_username.lower().lstrip("@")
    chat_id = _username_to_chat_id.get(username)

    if not chat_id:
        logger.warning(f"[TelegramBot] No chat_id found for @{username}. User must /start the bot first.")
        return False

    try:
        await _app.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🔐 Your UDX verification code:\n\n"
                f"  `{otp_code}`\n\n"
                f"This code expires in 5 minutes. Do not share it with anyone."
            ),
            parse_mode="Markdown"
        )
        logger.info(f"[TelegramBot] OTP sent to @{username} (chat_id={chat_id})")
        return True
    except Exception as e:
        logger.error(f"[TelegramBot] Failed to send OTP to @{username}: {e}")
        return False


def get_chat_id(telegram_username: str) -> int | None:
    """Return stored chat_id for a given Telegram username, or None."""
    username = telegram_username.lower().lstrip("@")
    return _username_to_chat_id.get(username)


async def start_bot() -> None:
    """Initialize and start the Telegram bot (non-blocking polling)."""
    global _app

    # Read token at runtime so load_dotenv() has already run
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.warning("[TelegramBot] TELEGRAM_BOT_TOKEN not set. Bot will not start.")
        return

    try:
        _app = Application.builder().token(token).build()
        _app.add_handler(CommandHandler("start", _start_handler))
        _app.add_handler(MessageHandler(filters.CONTACT, _contact_handler))

        await _app.initialize()
        await _app.start()
        # drop_pending_updates=False so we don't lose /start commands sent while offline
        await _app.updater.start_polling(drop_pending_updates=False)
        logger.info("[TelegramBot] Bot is now polling for updates.")
    except Exception as e:
        logger.error(f"[TelegramBot] Failed to start bot: {e}")
        _app = None


async def stop_bot() -> None:
    """Gracefully shut down the Telegram bot."""
    global _app
    if _app:
        try:
            await _app.updater.stop()
            await _app.stop()
            await _app.shutdown()
            logger.info("[TelegramBot] Bot stopped.")
        except Exception as e:
            logger.error(f"[TelegramBot] Error stopping bot: {e}")
        finally:
            _app = None
