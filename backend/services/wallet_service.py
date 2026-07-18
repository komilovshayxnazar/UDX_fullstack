"""
wallet_service.py — Wallet microservice logic.

Responsible for:
  - Balance read / update
  - Transaction recording
  - Publishing wallet events

In a full microservices setup this becomes a separate process
(e.g. wallet-service on port 8001) called via gRPC or internal HTTP.
Here it is a service layer within the monolith — same interface, easy to extract later.
"""

import uuid
from datetime import datetime, timezone

import models
from services.event_bus import event_bus


async def get_balance(user: models.User) -> float:
    return user.balance


async def credit(user: models.User, amount: float, card_token: str, idempotency_key: str | None = None) -> models.Transaction:
    """Add funds to user balance and record transaction."""
    txn = models.Transaction(
        user_id=str(user.id),
        amount=amount,
        type=models.TransactionType.deposit,
        status=models.TransactionStatus.success,
        card_token=card_token,
        transaction_id=f"txn_{uuid.uuid4().hex[:12]}"
    )
    await txn.insert()

    user.balance += amount
    await user.save()

    await event_bus.publish("wallet.credited", {
        "user_id": str(user.id),
        "amount": amount,
        "transaction_id": txn.transaction_id,
        "idempotency_key": idempotency_key,
    })
    return txn


async def debit(user: models.User, amount: float, card_token: str) -> models.Transaction:
    """Remove funds from user balance and record transaction."""
    if user.balance < amount:
        raise ValueError(f"Insufficient funds: balance={user.balance}, requested={amount}")
    txn = models.Transaction(
        user_id=str(user.id),
        amount=amount,
        type=models.TransactionType.withdraw,
        status=models.TransactionStatus.success,
        card_token=card_token,
        transaction_id=f"txn_wd_{uuid.uuid4().hex[:12]}"
    )
    await txn.insert()

    user.balance -= amount
    await user.save()

    await event_bus.publish("wallet.debited", {
        "user_id": str(user.id),
        "amount": amount,
        "transaction_id": txn.transaction_id,
    })
    return txn
