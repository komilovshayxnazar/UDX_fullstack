"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-22

Hand-written initial migration (no live Postgres available to run
--autogenerate against). Mirrors backend/models.py exactly.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')

    # create_type=False on every enum below — they are created explicitly
    # once via enum_type.create(...) right after this block. Without it,
    # SQLAlchemy re-issues CREATE TYPE for each column that uses the enum
    # (once per create_table call), which fails with "type already exists".
    user_role = postgresql.ENUM("buyer", "seller", "admin", name="user_role", create_type=False)
    order_status = postgresql.ENUM("new", "in-process", "completed", "cancelled", name="order_status", create_type=False)
    delivery_method = postgresql.ENUM("courier", "pickup", name="delivery_method", create_type=False)
    interaction_type = postgresql.ENUM("view", "click", "purchase", name="interaction_type", create_type=False)
    contract_status = postgresql.ENUM("active", "pending", "completed", "cancelled", name="contract_status", create_type=False)
    audit_action = postgresql.ENUM(
        "deposit", "withdraw", "card_added", "card_deleted",
        "login", "login_failed", "password_change", "profile_update",
        name="audit_action", create_type=False,
    )
    transaction_type = postgresql.ENUM("deposit", "withdraw", name="transaction_type", create_type=False)
    wallet_txn_type = postgresql.ENUM("deposit", "withdraw", name="wallet_txn_type", create_type=False)
    payment_method = postgresql.ENUM("card", "click", "wallet", name="payment_method", create_type=False)
    payment_status = postgresql.ENUM(
        "pending", "prepared", "success", "completed", "failed", "cancelled",
        name="payment_status", create_type=False,
    )

    bind = op.get_bind()
    for enum_type in (
        user_role, order_status, delivery_method, interaction_type,
        contract_status, audit_action, transaction_type, wallet_txn_type,
        payment_method, payment_status,
    ):
        enum_type.create(bind, checkfirst=True)

    # ── users ────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("phone_hash", sa.String(), nullable=False, server_default=""),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("telegram_username", sa.String(), nullable=True),
        sa.Column("telegram_username_hash", sa.String(), nullable=True),
        sa.Column("tin", sa.String(), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=True),
        sa.Column("role", user_role, nullable=False, server_default="buyer"),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("avatar", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_2fa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_online", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("distance", sa.Float(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=False, server_default="0"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("phone", name="uq_users_phone"),
        sa.UniqueConstraint("phone_hash", name="uq_users_phone_hash"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_phone_hash", "users", ["phone_hash"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_telegram_username_hash", "users", ["telegram_username_hash"])

    # ── payment_cards ────────────────────────────────────────────────────
    op.create_table(
        "payment_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_name", sa.String(), nullable=False),
        sa.Column("last4", sa.String(), nullable=False),
        sa.Column("expiry", sa.String(), nullable=False),
        sa.Column("card_type", sa.String(), nullable=False),
        sa.Column("card_token", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_payment_cards_user_id", "payment_cards", ["user_id"])

    # ── categories ───────────────────────────────────────────────────────
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("icon", sa.String(), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
    )

    # ── products ─────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("b2c_price", sa.Float(), nullable=False),
        sa.Column("b2b_price", sa.Float(), nullable=True),
        sa.Column("stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column("image", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("certified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_b2b", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rating", sa.Float(), nullable=False, server_default="0"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sales", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gallery", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_products_seller_id", "products", ["seller_id"])
    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.create_index("ix_products_title", "products", ["title"])

    # ── price_history ────────────────────────────────────────────────────
    op.create_table(
        "price_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_price_history_product_id", "price_history", ["product_id"])
    op.create_index("ix_price_history_changed_at", "price_history", ["changed_at"])

    # ── orders / order_items ─────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("status", order_status, nullable=False, server_default="new"),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("delivery_method", delivery_method, nullable=False, server_default="courier"),
    )
    op.create_index("ix_orders_buyer_id", "orders", ["buyer_id"])
    op.create_index("ix_orders_seller_id", "orders", ["seller_id"])

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("product_name", sa.String(), nullable=True),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    # ── contracts ────────────────────────────────────────────────────────
    op.create_table(
        "contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("status", contract_status, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_contracts_buyer_id", "contracts", ["buyer_id"])
    op.create_index("ix_contracts_seller_id", "contracts", ["seller_id"])

    # ── reviews ──────────────────────────────────────────────────────────
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("is_verified_purchase", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("order_id", name="uq_reviews_order_id"),
    )
    op.create_index("ix_reviews_seller_id", "reviews", ["seller_id"])
    op.create_index("ix_reviews_reviewer_id", "reviews", ["reviewer_id"])

    # ── fraud_reports ────────────────────────────────────────────────────
    op.create_table(
        "fraud_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reported_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reported_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_fraud_reports_reporter_id", "fraud_reports", ["reporter_id"])
    op.create_index("ix_fraud_reports_reported_user_id", "fraud_reports", ["reported_user_id"])
    op.create_index("ix_fraud_reports_reported_product_id", "fraud_reports", ["reported_product_id"])

    # ── chats / chat_messages ────────────────────────────────────────────
    op.create_table(
        "chats",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("other_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_message", sa.Text(), nullable=True),
        sa.Column("last_message_time", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("unread_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_chats_user_id", "chats", ["user_id"])
    op.create_index("ix_chats_other_user_id", "chats", ["other_user_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
    op.create_index("ix_chat_messages_sent_at", "chat_messages", ["sent_at"])

    # ── product_interactions ─────────────────────────────────────────────
    op.create_table(
        "product_interactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("interaction_type", interaction_type, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_product_interactions_user_id", "product_interactions", ["user_id"])
    op.create_index("ix_product_interactions_product_id", "product_interactions", ["product_id"])

    # ── payments ─────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("method", payment_method, nullable=False),
        sa.Column("type", transaction_type, nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("status", payment_status, nullable=False, server_default="pending"),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("merchant_trans_id", sa.String(), nullable=True),
        sa.Column("click_trans_id", sa.String(), nullable=True),
        sa.Column("click_paydoc_id", sa.String(), nullable=True),
        sa.Column("card_token", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
        sa.UniqueConstraint("merchant_trans_id", name="uq_payments_merchant_trans_id"),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"])

    # ── wallets / wallet_transactions ────────────────────────────────────
    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("user_id", name="uq_wallets_user_id"),
    )

    op.create_table(
        "wallet_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("type", wallet_txn_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_wallet_transactions_wallet_id", "wallet_transactions", ["wallet_id"])
    op.create_index("ix_wallet_transactions_created_at", "wallet_transactions", ["created_at"])

    # ── audit_log ────────────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", audit_action, nullable=False),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("entity_id", sa.String(), nullable=True),
        sa.Column("detail", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("ip_address", sa.String(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_actor_id", "audit_log", ["actor_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # ── idempotency_keys (generic, non-payment) ─────────────────────────
    op.create_table(
        "idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("key", "user_id", name="uq_idempotency_key_user"),
    )
    op.create_index("ix_idempotency_keys_created_at", "idempotency_keys", ["created_at"])


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("audit_log")
    op.drop_table("wallet_transactions")
    op.drop_table("wallets")
    op.drop_table("payments")
    op.drop_table("product_interactions")
    op.drop_table("chat_messages")
    op.drop_table("chats")
    op.drop_table("fraud_reports")
    op.drop_table("reviews")
    op.drop_table("contracts")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("price_history")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_table("payment_cards")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_name in (
        "payment_status", "payment_method", "wallet_txn_type", "transaction_type",
        "audit_action", "contract_status", "interaction_type", "delivery_method",
        "order_status", "user_role",
    ):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
