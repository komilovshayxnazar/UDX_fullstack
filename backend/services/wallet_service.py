"""
wallet_service.py — Wallet microservice logic.

Responsible for:
  - Balance read / update (Wallet.balance — balance no longer lives on User)
  - Transaction recording (Payment row + WalletTransaction ledger row)
  - Publishing wallet events

In a full microservices setup this becomes a separate process
(e.g. wallet-service on port 8001) called via gRPC or internal HTTP.
Here it is a service layer within the monolith — same interface, easy to extract later.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import models
from services.event_bus import event_bus


async def _get_or_create_wallet(db: AsyncSession, user_id: uuid.UUID) -> models.Wallet:
    result = await db.execute(select(models.Wallet).where(models.Wallet.user_id == user_id))
    wallet = result.scalar_one_or_none()
    if wallet is None:
        wallet = models.Wallet(user_id=user_id, balance=0.0)
        db.add(wallet)
        await db.flush()
    return wallet


async def get_balance(db: AsyncSession, user: models.User) -> float:
    wallet = await _get_or_create_wallet(db, user.id)
    return wallet.balance


async def credit(
    db: AsyncSession,
    user: models.User,
    amount: float,
    card_token: str,
    idempotency_key: str | None = None,
    method: models.PaymentMethod = models.PaymentMethod.card,
) -> models.Payment:
    """Add funds to the user's wallet and record a ledger entry."""
    payment = models.Payment(
        user_id=user.id,
        method=method,
        type=models.TransactionType.deposit,
        status=models.PaymentStatus.success,
        amount=amount,
        card_token=card_token,
    )
    db.add(payment)
    await db.flush()

    wallet = await _get_or_create_wallet(db, user.id)
    wallet.balance += amount

    wallet_txn = models.WalletTransaction(
        wallet_id=wallet.id,
        payment_id=payment.id,
        amount=amount,
        type=models.TransactionType.deposit,
    )
    db.add(wallet_txn)
    await db.commit()
    await db.refresh(payment)

    await event_bus.publish("wallet.credited", {
        "user_id": str(user.id),
        "amount": amount,
        "transaction_id": str(payment.id),
        "idempotency_key": idempotency_key,
    })
    return payment


async def debit(
    db: AsyncSession,
    user: models.User,
    amount: float,
    card_token: str,
    method: models.PaymentMethod = models.PaymentMethod.card,
) -> models.Payment:
    """Remove funds from the user's wallet and record a ledger entry."""
    wallet = await _get_or_create_wallet(db, user.id)
    if wallet.balance < amount:
        raise ValueError(f"Insufficient funds: balance={wallet.balance}, requested={amount}")

    payment = models.Payment(
        user_id=user.id,
        method=method,
        type=models.TransactionType.withdraw,
        status=models.PaymentStatus.success,
        amount=amount,
        card_token=card_token,
    )
    db.add(payment)
    await db.flush()

    wallet.balance -= amount

    wallet_txn = models.WalletTransaction(
        wallet_id=wallet.id,
        payment_id=payment.id,
        amount=amount,
        type=models.TransactionType.withdraw,
    )
    db.add(wallet_txn)
    await db.commit()
    await db.refresh(payment)

    await event_bus.publish("wallet.debited", {
        "user_id": str(user.id),
        "amount": amount,
        "transaction_id": str(payment.id),
    })
    return payment
