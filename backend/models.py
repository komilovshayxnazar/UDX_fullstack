"""
models.py — SQLAlchemy 2.0 declarative models (PostgreSQL).

Replaces the old Beanie/Mongo `Document` classes. UUID primary keys with a
server-side `gen_random_uuid()` default (see alembic/versions/0001_initial.py
for the `CREATE EXTENSION IF NOT EXISTS pgcrypto` this relies on).

The plain Python `Enum` classes below are reused directly as SQLAlchemy
`Enum` column types, so router code that references e.g. `models.OrderStatus
.new` keeps working unchanged.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid_pk():
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    buyer = "buyer"
    seller = "seller"
    admin = "admin"


class OrderStatus(str, Enum):
    new = "new"
    in_process = "in-process"
    completed = "completed"
    cancelled = "cancelled"


class DeliveryMethod(str, Enum):
    courier = "courier"
    pickup = "pickup"


class InteractionType(str, Enum):
    view = "view"
    click = "click"
    purchase = "purchase"


class ContractStatus(str, Enum):
    active = "active"
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"


class ClickTxnStatus(str, Enum):
    pending = "pending"
    prepared = "prepared"
    completed = "completed"
    cancelled = "cancelled"


class AuditAction(str, Enum):
    deposit = "deposit"
    withdraw = "withdraw"
    card_added = "card_added"
    card_deleted = "card_deleted"
    login = "login"
    login_failed = "login_failed"
    password_change = "password_change"
    profile_update = "profile_update"


class TransactionType(str, Enum):
    deposit = "deposit"
    withdraw = "withdraw"


class TransactionStatus(str, Enum):
    success = "success"
    failed = "failed"


class PaymentMethod(str, Enum):
    card = "card"
    click = "click"
    wallet = "wallet"


class PaymentStatus(str, Enum):
    pending = "pending"
    prepared = "prepared"
    success = "success"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


# ─────────────────────────────────────────────────────────────────────────────
# users
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()

    # Shifrlangan maydonlar (AES-256-GCM) — phone/telegram_username stay
    # encrypted at rest; *_hash columns are HMAC-SHA256 lookup keys.
    phone: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    phone_hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False, default="")
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    telegram_username_hash: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    tin: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    hashed_password: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", native_enum=True, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=UserRole.buyer, nullable=False, index=True,
    )
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Seller specific fields
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    distance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    payment_cards: Mapped[List["PaymentCard"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    wallet: Mapped[Optional["Wallet"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class PaymentCard(Base):
    """Tokenized card on file (never the real PAN) — kept as its own table
    so user card management keeps working post-migration."""
    __tablename__ = "payment_cards"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_name: Mapped[str] = mapped_column(String, nullable=False)
    last4: Mapped[str] = mapped_column(String, nullable=False)
    expiry: Mapped[str] = mapped_column(String, nullable=False)
    card_type: Mapped[str] = mapped_column(String, nullable=False)
    card_token: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="payment_cards")


# ─────────────────────────────────────────────────────────────────────────────
# categories / products / price_history
# ─────────────────────────────────────────────────────────────────────────────

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String, nullable=False)
    icon: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = _uuid_pk()
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String, index=True, nullable=False)
    b2c_price: Mapped[float] = mapped_column(Float, nullable=False)
    b2b_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    image: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    certified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_b2b: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sales: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    gallery: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    region: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[uuid.UUID] = _uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)


# ─────────────────────────────────────────────────────────────────────────────
# orders / order_items
# ─────────────────────────────────────────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = _uuid_pk()
    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    seller_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status", native_enum=True, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=OrderStatus.new, nullable=False,
    )
    total: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_method: Mapped[DeliveryMethod] = mapped_column(
        SAEnum(DeliveryMethod, name="delivery_method", native_enum=True, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=DeliveryMethod.courier, nullable=False,
    )

    items: Mapped[List["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = _uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    product_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="items")


# ─────────────────────────────────────────────────────────────────────────────
# contracts
# ─────────────────────────────────────────────────────────────────────────────

class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)

    title: Mapped[str] = mapped_column(String, nullable=False)
    terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[ContractStatus] = mapped_column(
        SAEnum(ContractStatus, name="contract_status", native_enum=True, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=ContractStatus.pending, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


# ─────────────────────────────────────────────────────────────────────────────
# reviews / fraud_reports
# ─────────────────────────────────────────────────────────────────────────────

class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("order_id", name="uq_reviews_order_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified_purchase: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class FraudReport(Base):
    __tablename__ = "fraud_reports"

    id: Mapped[uuid.UUID] = _uuid_pk()
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reported_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reported_product_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


# ─────────────────────────────────────────────────────────────────────────────
# chats / chat_messages
# ─────────────────────────────────────────────────────────────────────────────

class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    other_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    last_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_message_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    unread_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    messages: Mapped[List["ChatMessage"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = _uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    conversation: Mapped["Chat"] = relationship(back_populates="messages")


# ─────────────────────────────────────────────────────────────────────────────
# product_interactions (kept — feeds SVD + SQL CF recommendations)
# ─────────────────────────────────────────────────────────────────────────────

class ProductInteraction(Base):
    __tablename__ = "product_interactions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    interaction_type: Mapped[InteractionType] = mapped_column(
        SAEnum(InteractionType, name="interaction_type", native_enum=True, values_callable=lambda enum_cls: [e.value for e in enum_cls]), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


# ─────────────────────────────────────────────────────────────────────────────
# payments (merges old Transaction + ClickTransaction)
# ─────────────────────────────────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = _uuid_pk()
    # nullable — wallet top-ups / withdrawals have no associated order
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)

    method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(PaymentMethod, name="payment_method", native_enum=True, values_callable=lambda enum_cls: [e.value for e in enum_cls]), nullable=False
    )
    type: Mapped[Optional[TransactionType]] = mapped_column(
        SAEnum(TransactionType, name="transaction_type", native_enum=True, values_callable=lambda enum_cls: [e.value for e in enum_cls]), nullable=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status", native_enum=True, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=PaymentStatus.pending, nullable=False,
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)

    merchant_trans_id: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    click_trans_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    click_paydoc_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    card_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


# ─────────────────────────────────────────────────────────────────────────────
# wallets / wallet_transactions
# ─────────────────────────────────────────────────────────────────────────────

class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="wallet")
    transactions: Mapped[List["WalletTransaction"]] = relationship(back_populates="wallet", cascade="all, delete-orphan")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, name="wallet_txn_type", native_enum=True, values_callable=lambda enum_cls: [e.value for e in enum_cls]), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    wallet: Mapped["Wallet"] = relationship(back_populates="transactions")


# ─────────────────────────────────────────────────────────────────────────────
# audit_log
# ─────────────────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = _uuid_pk()
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction, name="audit_action", native_enum=True, values_callable=lambda enum_cls: [e.value for e in enum_cls]), nullable=False, index=True
    )
    entity_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    detail: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ip_address: Mapped[str] = mapped_column(String, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)


# ─────────────────────────────────────────────────────────────────────────────
# idempotency_keys — generic, non-payment idempotency (e.g. order creation).
# Payment-flow idempotency lives directly on payments.idempotency_key.
# ─────────────────────────────────────────────────────────────────────────────

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("key", "user_id", name="uq_idempotency_key_user"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    key: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
