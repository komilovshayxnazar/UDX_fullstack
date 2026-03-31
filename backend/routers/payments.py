"""
payments.py — Payment router.

Features implemented:
  ✅ Idempotency keys      (X-Idempotency-Key header)
  ✅ Rate limiting         (5 payment attempts / minute per IP)
  ✅ Audit logs            (every action recorded)
  ✅ Event-driven          (payment_service publishes events)
  ✅ Retry mechanism       (payment_service retries gateway up to 3×)
  ✅ Service separation    (wallet_service / payment_service)
"""

import secrets
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Request

import models
import schemas
from core.dependencies import get_current_user
from core.rate_limiter import limiter
from services import payment_service, wallet_service
from services.audit_service import log as audit_log

router = APIRouter(prefix="/payments", tags=["payments"])


# ── Mock gateway tokenization ──────────────────────────────────────────────────

@router.post("/tokenize", response_model=schemas.CardTokenizeResponse)
@limiter.limit("20/minute")
async def tokenize_card(request: Request, card: schemas.CardTokenizeRequest):
    """
    MOCK GATEWAY — converts a card number into an opaque token.
    In production, this call goes directly to the real payment gateway SDK
    (Click.js / Stripe.js) from the client — our server never sees the PAN.
    """
    digits = card.card_number
    card_type = {"4": "Visa", "5": "Mastercard", "3": "Amex"}.get(digits[0], "Other")
    token = f"tok_{secrets.token_hex(16)}"
    return schemas.CardTokenizeResponse(
        card_token=token,
        last4=digits[-4:],
        card_type=card_type,
        expiry=card.expiry,
        owner_name=card.owner_name
    )


# ── Deposit (top-up) ───────────────────────────────────────────────────────────

@router.post("/deposit", response_model=schemas.User)
@limiter.limit("5/minute")
async def deposit(
    request: Request,
    body: schemas.TransactionRequest,
    idempotency_key: str = Header(default=None, alias="X-Idempotency-Key"),
    current_user: models.User = Depends(get_current_user),
):
    """
    Top-up balance.

    Client MUST send a unique X-Idempotency-Key (UUID) per payment attempt.
    Duplicate requests with the same key return the original response immediately
    without re-charging the card (prevents double payments on network retry).
    """
    if not idempotency_key:
        idempotency_key = str(uuid.uuid4())   # auto-generate if client forgot

    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    card = next((c for c in current_user.payment_cards if c.id == body.card_id), None)
    if not card:
        raise HTTPException(status_code=400, detail="Card not found. Add a payment card first.")

    # payment_service handles: idempotency check + gateway retry + audit log + events
    result = await payment_service.charge_card(
        user=current_user,
        card=card,
        amount=body.amount,
        idempotency_key=idempotency_key,
        request=request,
    )

    if result["status"] != "success":
        raise HTTPException(status_code=402, detail="Payment gateway declined the charge.")

    # Skip credit on idempotent replay — balance must not increase again
    if not result.get("_replay"):
        await wallet_service.credit(
            user=current_user,
            amount=body.amount,
            card_token=card.card_token,
            idempotency_key=idempotency_key,
        )

    return await models.User.get(current_user.id)


# ── Withdraw ───────────────────────────────────────────────────────────────────

@router.post("/withdraw", response_model=schemas.User)
@limiter.limit("5/minute")
async def withdraw(
    request: Request,
    body: schemas.TransactionRequest,
    current_user: models.User = Depends(get_current_user),
):
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if current_user.balance < body.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    card = next((c for c in current_user.payment_cards if c.id == body.card_id), None)
    if not card:
        raise HTTPException(status_code=400, detail="Card not found.")

    await wallet_service.debit(
        user=current_user,
        amount=body.amount,
        card_token=card.card_token,
    )

    await audit_log(
        user=current_user,
        action=models.AuditAction.withdraw,
        detail={"amount": body.amount, "card_last4": card.last4},
        request=request,
    )

    return current_user


# ── Transaction history ────────────────────────────────────────────────────────

@router.get("/transactions", response_model=list[schemas.TransactionOut])
async def get_transactions(current_user: models.User = Depends(get_current_user)):
    txns = await models.Transaction.find(
        models.Transaction.user_id == str(current_user.id)
    ).sort(-models.Transaction.created_at).to_list()

    return [
        schemas.TransactionOut(
            id=str(t.id),
            amount=t.amount,
            type=t.type.value,
            status=t.status.value,
            transaction_id=t.transaction_id,
            created_at=t.created_at.isoformat()
        )
        for t in txns
    ]


# ── Audit log (admin / user self-service) ─────────────────────────────────────

@router.get("/audit", response_model=list[schemas.AuditLogOut])
async def get_audit_log(current_user: models.User = Depends(get_current_user)):
    """Returns the last 50 audit entries for the current user."""
    entries = await models.AuditLog.find(
        models.AuditLog.user_id == str(current_user.id)
    ).sort(-models.AuditLog.created_at).limit(50).to_list()

    return [
        schemas.AuditLogOut(
            id=str(e.id),
            action=e.action.value,
            detail=e.detail,
            ip_address=e.ip_address,
            success=e.success,
            created_at=e.created_at.isoformat()
        )
        for e in entries
    ]
