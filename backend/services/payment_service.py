"""
payment_service.py — Payment microservice logic.

Responsible for:
  - Calling the payment gateway (with retry + exponential backoff)
  - Idempotency key enforcement (no double charges) — enforced directly
    against `payments.idempotency_key` (unique) rather than a separate
    generic table, since a card charge always produces a Payment row.
  - Audit logging every payment action
  - Publishing payment events

`get_idempotency_record` / `save_idempotency_record` below still operate on
the standalone `idempotency_keys` table — that one is kept for generic,
non-payment idempotent actions (e.g. order creation in routers/orders.py)
that don't naturally produce a Payment row.

In a full microservices setup this is payment-service (separate process).
"""

import asyncio
import json
import logging
import os
import secrets

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import models
from services.event_bus import event_bus

logger = logging.getLogger("payment_service")

# ── Retry configuration ────────────────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.5   # seconds

# ── Environment gate ──────────────────────────────────────────────────────────
_IS_PROD = os.getenv("ENVIRONMENT", "production").lower() == "production"
_GATEWAY_URL = os.getenv("PAYMENT_GATEWAY_URL", "").strip()
_ALLOW_MOCK = os.getenv("PAYMENT_ALLOW_MOCK", "").lower() in {"1", "true", "yes"}


# ── Mock gateway (replace with real HTTP call in production) ───────────────────
async def _gateway_charge_once(card_token: str, amount: float) -> dict:
    """
    Single attempt at the payment gateway.

    SAFETY: in production this MUST be replaced with a real HTTP call to
    the actual gateway. To avoid accidental deployments of the mock we
    refuse to charge unless either PAYMENT_GATEWAY_URL is set (real
    gateway configured elsewhere and the caller passes tokens issued by
    it) or PAYMENT_ALLOW_MOCK=1 has been set explicitly for a staging
    smoke-test.
    """
    if _IS_PROD and not _GATEWAY_URL and not _ALLOW_MOCK:
        logger.critical(
            "[PAYMENT] Refusing to charge — mock gateway in production. "
            "Set PAYMENT_GATEWAY_URL or PAYMENT_ALLOW_MOCK=1 explicitly."
        )
        raise HTTPException(
            status_code=503,
            detail="Payment gateway not configured. Contact support.",
        )
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


# ── Generic (non-payment) idempotency — orders.py order-creation dedup ────────
async def get_idempotency_record(db: AsyncSession, key: str, user_id) -> models.IdempotencyKey | None:
    result = await db.execute(
        select(models.IdempotencyKey).where(
            models.IdempotencyKey.key == key,
            models.IdempotencyKey.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def save_idempotency_record(db: AsyncSession, key: str, user_id, status: int, body: dict):
    record = models.IdempotencyKey(
        key=key,
        user_id=user_id,
        response_status=status,
        response_body=json.dumps(body),
    )
    db.add(record)
    try:
        await db.commit()
    except Exception:
        await db.rollback()   # unique index violation — another concurrent request already saved it


# ── Audit logging ──────────────────────────────────────────────────────────────
async def audit(
    db: AsyncSession,
    user: models.User,
    action: models.AuditAction,
    detail: dict,
    request: Request,
    success: bool,
    idempotency_key: str | None = None,
):
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    log = models.AuditLog(
        actor_id=user.id,
        action=action,
        detail=detail,
        ip_address=ip,
        success=success,
        idempotency_key=idempotency_key,
    )
    db.add(log)
    await db.flush()


# ── High-level payment operations ─────────────────────────────────────────────
async def charge_card(
    db: AsyncSession,
    user: models.User,
    card: models.PaymentCard,
    amount: float,
    idempotency_key: str,
    request: Request,
) -> dict:
    """
    Full deposit flow:
      1. Check idempotency key against `payments.idempotency_key` → return
         cached response if duplicate
      2. Call gateway (with retry)
      3. Persist the charge attempt as a Payment row
      4. Write audit log
      5. Publish event

    Returns dict with `_replay=True` when the key was already processed so the
    caller knows to skip the balance credit step (preventing double credit).
    """
    user_id = user.id

    # 1. Idempotency check
    result = await db.execute(
        select(models.Payment).where(
            models.Payment.idempotency_key == idempotency_key,
            models.Payment.user_id == user_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        logger.info(f"Idempotent replay for key={idempotency_key} user={user_id}")
        return {
            "status": "success" if existing.status == models.PaymentStatus.success else "failed",
            "transaction_id": existing.merchant_trans_id or str(existing.id),
            "_replay": True,
        }

    # 2. Gateway charge with retry
    gateway_result = await gateway_charge(card.card_token, amount)
    success = gateway_result["status"] == "success"

    # 3. Persist the charge attempt
    payment = models.Payment(
        user_id=user_id,
        method=models.PaymentMethod.card,
        type=models.TransactionType.deposit,
        status=models.PaymentStatus.success if success else models.PaymentStatus.failed,
        amount=amount,
        idempotency_key=idempotency_key,
        card_token=card.card_token,
        merchant_trans_id=gateway_result.get("transaction_id") or None,
    )
    db.add(payment)
    await db.flush()

    # 4. Audit log
    await audit(
        db,
        user=user,
        action=models.AuditAction.deposit,
        detail={
            "amount": amount,
            "card_last4": card.last4,
            "card_type": card.card_type,
            "transaction_id": gateway_result.get("transaction_id"),
            "gateway_status": gateway_result["status"],
        },
        request=request,
        success=success,
        idempotency_key=idempotency_key,
    )

    await db.commit()

    # 5. Event
    await event_bus.publish("payment.charged", {
        "user_id": str(user_id),
        "amount": amount,
        "transaction_id": gateway_result.get("transaction_id"),
        "success": success,
    })

    return {"status": gateway_result["status"], "transaction_id": gateway_result.get("transaction_id")}
