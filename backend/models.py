from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field
from beanie import Document
from pymongo import IndexModel
import pymongo

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

class PaymentCard(BaseModel):
    id: str
    owner_name: str
    last4: str
    expiry: str        # MM/YY
    card_type: str     # Visa / Mastercard / Amex / Other
    card_token: str    # Opaque gateway token — never the real PAN

class TransactionType(str, Enum):
    deposit = "deposit"
    withdraw = "withdraw"

class TransactionStatus(str, Enum):
    success = "success"
    failed = "failed"

class Transaction(Document):
    user_id: str
    amount: float
    type: TransactionType
    status: TransactionStatus
    card_token: str
    transaction_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "transactions"
        indexes = [
            IndexModel([("user_id", pymongo.ASCENDING)]),
            IndexModel([("created_at", pymongo.DESCENDING)])
        ]

class User(Document):
    phone: str
    hashed_password: Optional[str] = None
    role: UserRole = UserRole.buyer
    name: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool = True
    is_2fa_enabled: bool = False
    is_public: bool = True
    balance: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payment_cards: List[PaymentCard] = []

    telegram_username: Optional[str] = None

    # Seller specific fields
    description: Optional[str] = None
    tin: Optional[str] = None
    is_online: bool = False
    distance: Optional[float] = None
    rating: float = 0.0
    review_count: int = 0

    class Settings:
        name = "users"
        indexes = [
            IndexModel([("phone", pymongo.ASCENDING)], unique=True),
            IndexModel([("role", pymongo.ASCENDING)])
        ]

class Category(Document):
    name: str
    icon: str

    class Settings:
        name = "categories"

class Product(Document):
    seller_id: str  # Store as string ID for simpler queries without resolving links
    category_id: str
    
    name: str
    price: float
    unit: str
    image: str
    description: str
    in_stock: bool = True
    certified: bool = False
    is_b2b: bool = False
    
    rating: float = 0.0
    review_count: int = 0
    views: int = 0
    sales: int = 0
    
    gallery: List[str] = []
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "products"
        indexes = [
            IndexModel([("seller_id", pymongo.ASCENDING)]),
            IndexModel([("category_id", pymongo.ASCENDING)]),
            IndexModel([("name", pymongo.TEXT)])
        ]

class PriceHistory(Document):
    product_id: str
    price: float
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "price_history"
        indexes = [
            IndexModel([("product_id", pymongo.ASCENDING)]),
            IndexModel([("date", pymongo.ASCENDING)])
        ]

class OrderItem(BaseModel):
    product_id: str
    quantity: int
    price_at_purchase: float

class Order(Document):
    buyer_id: str
    seller_id: Optional[str] = None
    
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: OrderStatus = OrderStatus.new
    total: float
    delivery_method: DeliveryMethod = DeliveryMethod.courier
    
    items: List[OrderItem] = []  # Embedded documents! More efficient for NoSQL

    class Settings:
        name = "orders"
        indexes = [
            IndexModel([("buyer_id", pymongo.ASCENDING)]),
            IndexModel([("seller_id", pymongo.ASCENDING)])
        ]

class Chat(Document):
    user_id: str
    other_user_id: str
    product_id: Optional[str] = None
    last_message: Optional[str] = None
    last_message_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    unread_count: int = 0

    class Settings:
        name = "chats"
        indexes = [
            IndexModel([("user_id", pymongo.ASCENDING)]),
            IndexModel([("other_user_id", pymongo.ASCENDING)])
        ]

class Message(Document):
    chat_id: str
    sender_id: str
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "messages"
        indexes = [
            IndexModel([("chat_id", pymongo.ASCENDING)]),
            IndexModel([("timestamp", pymongo.ASCENDING)])
        ]

class Contract(Document):
    buyer_id: str
    seller_id: str
    title: str
    description: Optional[str] = None
    amount: float
    status: ContractStatus = ContractStatus.pending
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "contracts"
        indexes = [
            IndexModel([("buyer_id", pymongo.ASCENDING)]),
            IndexModel([("seller_id", pymongo.ASCENDING)])
        ]

class ProductInteraction(Document):
    user_id: str
    product_id: str
    interaction_type: InteractionType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "product_interactions"
        indexes = [
            IndexModel([("user_id", pymongo.ASCENDING)]),
            IndexModel([("product_id", pymongo.ASCENDING)])
        ]


class Review(Document):
    """
    Faqat tasdiqlangan xaridor (completed order) qoldira oladi.
    Har bir order uchun faqat 1 ta sharh — unique index orqali.
    """
    reviewer_id: str
    seller_id: str
    order_id: str                          # completed order — unique constraint
    product_id: Optional[str] = None
    rating: int                            # 1–5
    comment: str
    is_verified_purchase: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "reviews"
        indexes = [
            IndexModel([("seller_id", pymongo.ASCENDING)]),
            IndexModel([("reviewer_id", pymongo.ASCENDING)]),
            IndexModel([("order_id", pymongo.ASCENDING)], unique=True),
        ]


class FraudReport(Document):
    """Foydalanuvchi yoki mahsulotni shikoyat qilish."""
    reporter_id: str
    target_user_id: Optional[str] = None
    target_product_id: Optional[str] = None
    reason: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "fraud_reports"
        indexes = [
            IndexModel([("reporter_id", pymongo.ASCENDING)]),
            IndexModel([("target_user_id", pymongo.ASCENDING)]),
            IndexModel([("target_product_id", pymongo.ASCENDING)]),
        ]


class IdempotencyKey(Document):
    """
    Prevents double payments.
    Client generates a UUID per payment attempt and sends it as X-Idempotency-Key.
    On first request: process and store result.
    On duplicate request: return stored result immediately without re-charging.
    """
    key: str
    user_id: str
    response_status: int
    response_body: str          # JSON-serialised response
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "idempotency_keys"
        indexes = [
            IndexModel([("key", pymongo.ASCENDING), ("user_id", pymongo.ASCENDING)], unique=True),
            # TTL: auto-delete after 24 h (MongoDB TTL index)
            IndexModel([("created_at", pymongo.ASCENDING)], expireAfterSeconds=86400)
        ]


class AuditAction(str, Enum):
    deposit         = "deposit"
    withdraw        = "withdraw"
    card_added      = "card_added"
    card_deleted    = "card_deleted"
    login           = "login"
    password_change = "password_change"
    profile_update  = "profile_update"


class AuditLog(Document):
    """
    Immutable audit trail — never updated, only inserted.
    Answers: who did what, when, from which IP, with what result.
    """
    user_id: str
    action: AuditAction
    detail: dict                # free-form payload (amount, card last4, etc.)
    ip_address: str
    success: bool
    idempotency_key: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "audit_logs"
        indexes = [
            IndexModel([("user_id", pymongo.ASCENDING)]),
            IndexModel([("action", pymongo.ASCENDING)]),
            IndexModel([("created_at", pymongo.DESCENDING)])
        ]
