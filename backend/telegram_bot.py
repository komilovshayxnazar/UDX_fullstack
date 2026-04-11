"""
Telegram Bot for UDX OTP Delivery.

Flow:
  1. User opens Telegram and sends /start to the UDX bot.
  2. Bot stores their chat_id mapped to their Telegram username (persisted to disk).
  3. When the user requests an OTP on signup, the backend calls send_otp()
     which sends the 6-digit code directly to the user in Telegram.
"""

import os
import json
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

# Persist chat_id mappings so they survive server restarts
_STORE_PATH = Path(__file__).parent / "telegram_chat_ids.json"

def _load_store() -> dict[str, int]:
    if _STORE_PATH.exists():
        try:
            return json.loads(_STORE_PATH.read_text())
        except Exception:
            pass
    return {}

def _save_store(store: dict[str, int]) -> None:
    try:
        _STORE_PATH.write_text(json.dumps(store))
    except Exception as e:
        logger.error(f"[TelegramBot] Failed to persist chat_id store: {e}")

# In-memory + on-disk store: { telegram_username (lowercase) -> chat_id }
_username_to_chat_id: dict[str, int] = _load_store()

# Token store: { token -> chat_id } — set when user taps Start with a token
# OTP sending is triggered from auth.py after this is populated
_token_to_chat_id: dict[str, int] = {}

# Global Application reference (set when bot starts)
_app: Application | None = None


async def _start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start [token] — register chat_id by token (phone-based flow)."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    args = context.args  # payload after /start

    if args:
        # Phone-based flow: /start TOKEN
        token = args[0].strip()
        _token_to_chat_id[token] = chat_id
        logger.info(f"[TelegramBot] Token {token!r} mapped to chat_id={chat_id}")
        await update.message.reply_text(
            "✅ Tayyor! Tasdiqlash kodi hozir yuborilmoqda...\n\n"
            "Kodni olgach, ilovaga qaytib kiriting 📱"
        )
        # Notify auth.py that the user arrived — it will send OTP via callback
        if _on_token_arrived:
            import asyncio
            asyncio.create_task(_on_token_arrived(token, chat_id))
    elif user and user.username:
        # Legacy username-based flow
        username = user.username.lower().lstrip("@")
        _username_to_chat_id[username] = chat_id
        _save_store(_username_to_chat_id)
        logger.info(f"[TelegramBot] Registered chat_id for @{username}: {chat_id}")
        await update.message.reply_text(
            "✅ Tayyor! UDX da ro'yxatdan o'tish kodi shu yerga yuboriladi.\n\n"
            "Ilovaga qaytib ro'yxatdan o'tishni davom eting 🚀"
        )
    else:
        await update.message.reply_text(
            "UDX ilovasidan ro'yxatdan o'tish uchun bu botni oching.\n"
            "Agar muammo bo'lsa, ilovadagi yo'riqnomani ko'ring."
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
