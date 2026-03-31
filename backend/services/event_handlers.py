"""
event_handlers.py — Subscribe to domain events published by payment/wallet services.

Add new handlers here as the system grows (notifications, analytics, fraud detection).
This file is imported once in main.py so handlers register at startup.
"""

import logging
from services.event_bus import event_bus

logger = logging.getLogger("event_handlers")


@event_bus.on("payment.charged")
async def on_payment_charged(payload: dict):
    """Fired when the gateway processes a charge (success or failure)."""
    status = "✅ success" if payload.get("success") else "❌ failed"
    logger.info(
        f"[EVENT] payment.charged | user={payload.get('user_id')} "
        f"amount={payload.get('amount')} txn={payload.get('transaction_id')} {status}"
    )
    # Future: send push notification, trigger fraud check, update analytics


@event_bus.on("wallet.credited")
async def on_wallet_credited(payload: dict):
    """Fired after balance is successfully increased."""
    logger.info(
        f"[EVENT] wallet.credited | user={payload.get('user_id')} "
        f"amount={payload.get('amount')} txn={payload.get('transaction_id')}"
    )
    # Future: send Telegram notification, update loyalty points


@event_bus.on("wallet.debited")
async def on_wallet_debited(payload: dict):
    """Fired after balance is successfully decreased."""
    logger.info(
        f"[EVENT] wallet.debited | user={payload.get('user_id')} "
        f"amount={payload.get('amount')} txn={payload.get('transaction_id')}"
    )
    # Future: receipt generation, accounting sync
