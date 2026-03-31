"""
payment_service.py — Payment microservice logic.

Responsible for:
  - Calling the payment gateway (with retry + exponential backoff)
  - Idempotency key enforcement (no double charges)
  - Audit logging every payment action
  - Publishing payment events

In a full microservices setup this is payment-service (separate process).
"""

import asyncio
import json
import logging
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, Request

import models
from services.event_bus import event_bus

logger = logging.getLogger("payment_service")

# ── Retry configuration ────────────────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.5   # seconds


# ── Mock gateway (replace with real HTTP call in production) ───────────────────
async def _gateway_charge_once(card_token: str, amount: float) -> dict:
    """Single attempt at the payment gateway."""
    if not card_token.startswith("tok_"):
        return {"status": "failed", "transaction_id": ""}
    return {"status": "success", "transaction_id": f"txn_{secrets.token_hex(8)}"}


async def gateway_charge(card_token: str, amount: float) -> dict:
    """
    Gateway call with exponential-backoff retry.
    Retries on transient network / 5xx errors up to MAX_RETRIES times.
    Raises HTTPException(502) if all attempts fail.
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = await _gateway_charge_once(card_token, amount)
            if result["status"] == "success":
                return result
            # Gateway returned a hard decline — do not retry
            return result
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))   # 0.5 → 1 → 2 s
                logger.warning(f"Gateway attempt {attempt} failed ({e}), retrying in {delay}s")
                await asyncio.sleep(delay)

    logger.error(f"All {MAX_RETRIES} gateway attempts failed: {last_error}")
    raise HTTPException(status_code=502, detail="Payment gateway unavailable. Please try again.")


# ── Idempotency ────────────────────────────────────────────────────────────────
async def get_idempotency_record(key: str, user_id: str) -> models.IdempotencyKey | None:
    return await models.IdempotencyKey.find_one(
        models.IdempotencyKey.key == key,
        models.IdempotencyKey.user_id == user_id
    )


async def save_idempotency_record(key: str, user_id: str, status: int, body: dict):
    record = models.IdempotencyKey(
        key=key,
        user_id=user_id,
        response_status=status,
        response_body=json.dumps(body)
    )
    try:
        await record.insert()
    except Exception:
        pass   # unique index violation — another concurrent request already saved it


# ── Audit logging ──────────────────────────────────────────────────────────────
async def audit(
    user: models.User,
    action: models.AuditAction,
    detail: dict,
    request: Request,
    success: bool,
    idempotency_key: str | None = None,
):
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    log = models.AuditLog(
        user_id=str(user.id),
        action=action,
        detail=detail,
        ip_address=ip,
        success=success,
        idempotency_key=idempotency_key
    )
    await log.insert()


# ── High-level payment operations ─────────────────────────────────────────────
async def charge_card(
    user: models.User,
    card: models.PaymentCard,
    amount: float,
    idempotency_key: str,
    request: Request,
) -> dict:
    """
    Full deposit flow:
      1. Check idempotency key → return cached response if duplicate
      2. Call gateway (with retry)
      3. Write audit log
      4. Publish event
      5. Save idempotency result

    Returns dict with `_replay=True` when the key was already processed so the
    caller knows to skip the balance credit step (preventing double credit).
    """
    user_id = str(user.id)

    # 1. Idempotency check
    existing = await get_idempotency_record(idempotency_key, user_id)
    if existing:
        logger.info(f"Idempotent replay for key={idempotency_key} user={user_id}")
        cached = json.loads(existing.response_body)
        cached["_replay"] = True
        return cached

    # 2. Gateway charge with retry
    result = await gateway_charge(card.card_token, amount)
    success = result["status"] == "success"

    # 3. Audit log
    await audit(
        user=user,
        action=models.AuditAction.deposit,
        detail={
            "amount": amount,
            "card_last4": card.last4,
            "card_type": card.card_type,
            "transaction_id": result.get("transaction_id"),
            "gateway_status": result["status"],
        },
        request=request,
        success=success,
        idempotency_key=idempotency_key,
    )

    # 4. Event
    await event_bus.publish("payment.charged", {
        "user_id": user_id,
        "amount": amount,
        "transaction_id": result.get("transaction_id"),
        "success": success,
    })

    # 5. Save idempotency result
    await save_idempotency_record(idempotency_key, user_id, 200 if success else 402, result)

    return result
