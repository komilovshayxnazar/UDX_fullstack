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

# Global Application reference (set when bot starts)
_app: Application | None = None


async def _start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command — register the user's chat_id."""
    user = update.effective_user
    if user and user.username:
        username = user.username.lower().lstrip("@")
        _username_to_chat_id[username] = update.effective_chat.id
        _save_store(_username_to_chat_id)
        logger.info(f"[TelegramBot] Registered chat_id for @{username}: {update.effective_chat.id}")
        await update.message.reply_text(
            "✅ You're all set! When you request a signup code on UDX, "
            "I'll send it to you here.\n\n"
            "Go back to the app and continue registration 🚀"
        )
    else:
        await update.message.reply_text(
            "⚠️ Your Telegram account needs a username for OTP delivery. "
            "Please set a username in Telegram settings and try again."
        )


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
