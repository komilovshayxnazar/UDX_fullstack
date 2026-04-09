from pydantic import BaseModel, field_validator
from typing import Any, List, Optional, TYPE_CHECKING
from datetime import datetime
import enum
import re

if TYPE_CHECKING:
    import models as _models


def user_to_schema(user: "_models.User") -> "User":
    """models.User → schemas.User (shifrlangan maydonlarni ochib beradi)."""
    from core.encryption import decrypt
    return User(
        id=str(user.id),
        phone=decrypt(user.phone) if user.phone else "",
        name=user.name,
        role=user.role.value,
        avatar=user.avatar,
        is_active=user.is_active,
        is_public=user.is_public,
        balance=user.balance,
        rating=user.rating,
    )

class MongoBase(BaseModel):
    """Barcha response schemalari uchun base class — ObjectId ni str ga o'giradi."""
    @field_validator('*', mode='before')
    @classmethod
    def coerce_objectid(cls, v: Any) -> Any:
        # bpy ObjectId yoki PydanticObjectId ni str ga o'giradi
        if hasattr(v, '__class__') and v.__class__.__name__ in ('ObjectId', 'PydanticObjectId'):
            return str(v)
        return v

    class Config:
        from_attributes = True

# Enums (mirroring models)
class UserRole(str, enum.Enum):
    buyer = "buyer"
    seller = "seller"

class OrderStatus(str, enum.Enum):
    new = "new"
    in_process = "in-process"
    completed = "completed"
    cancelled = "cancelled"

class InteractionType(str, enum.Enum):
    view = "view"
    click = "click"
    purchase = "purchase"

# Product Schemas
class ProductInteractionCreate(BaseModel):
    product_id: str
    interaction_type: InteractionType
class ProductBase(BaseModel):
    name: str
    price: float
    unit: str
    image: str
    description: str
    category_id: str
    in_stock: bool = True
    certified: bool = False
    is_b2b: bool = False
    gallery: List[str] = []

class ProductCreate(ProductBase):
    pass

class SellerPublic(MongoBase):
    id: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    rating: float = 0.0
    review_count: int = 0
    is_online: bool = False
    is_verified: bool = False   # True if seller has TIN registered

class Product(MongoBase, ProductBase):
    id: str
    seller_id: str
    rating: float
    review_count: int
    views: int
    sales: int
    distance: Optional[float] = None
    seller: Optional[SellerPublic] = None

class PriceHistoryBase(BaseModel):
    price: float

class PriceHistoryCreate(PriceHistoryBase):
    pass

class PriceHistory(MongoBase, PriceHistoryBase):
    id: str
    product_id: str
    date: datetime

# User Schemas
class UserBase(BaseModel):
    phone: str
    name: Optional[str] = None
    role: UserRole = UserRole.buyer

class UserCreate(UserBase):
    password: str
    telegram_username: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password strength:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)')
        
        return v

class UserLogin(BaseModel):
    phone: str
    password: str

class User(MongoBase, UserBase):
    id: str
    avatar: Optional[str] = None
    is_active: bool
    is_public: bool = True
    balance: float = 0.0
    rating: float = 0.0

class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None

class RoleUpdate(BaseModel):
    role: UserRole

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str

class PhoneUpdate(BaseModel):
    new_phone: str
    password: str

class TwoFactorUpdate(BaseModel):
    is_2fa_enabled: bool

# ── Payment / Tokenization Schemas ───────────────────────────────────────────
#
# Architecture (mirrors Click / Payme / Stripe):
#   1. Client sends card to POST /payments/tokenize  (mock gateway endpoint)
#   2. Gateway returns card_token — full PAN is never stored anywhere
#   3. Client sends card_token to POST /users/me/cards  (our server)
#   4. For top-up: client sends { amount, card_id } to POST /users/me/balance/deposit
#   5. Server calls internal charge with card_token → logs Transaction → updates balance
#
# In production, step 1 is replaced by the real SDK (Click JS, Stripe.js, etc.)
# and is called directly from the client without touching our server at all.

class CardTokenizeRequest(BaseModel):
    """
    MOCK GATEWAY ENDPOINT ONLY.
    In production this call goes directly to the real payment gateway SDK
    and never reaches our server — keeping us out of PCI DSS scope.
    """
    card_number: str
    expiry: str
    owner_name: str

    @field_validator('card_number')
    @classmethod
    def validate_pan(cls, v: str) -> str:
        digits = v.replace(' ', '').replace('-', '')
        if not digits.isdigit() or len(digits) not in (13, 15, 16):
            raise ValueError('Invalid card number')
        return digits

    @field_validator('expiry')
    @classmethod
    def validate_expiry(cls, v: str) -> str:
        if not re.match(r'^\d{2}/\d{2}$', v):
            raise ValueError('Expiry must be MM/YY')
        return v

class CardTokenizeResponse(BaseModel):
    card_token: str   # opaque token — use this everywhere instead of PAN
    last4: str
    card_type: str
    expiry: str
    owner_name: str

class PaymentCardCreate(BaseModel):
    """Stores a previously tokenized card against the user account."""
    card_token: str
    last4: str
    expiry: str
    owner_name: str
    card_type: str

class PaymentCardOut(MongoBase):
    id: str
    owner_name: str
    last4: str
    expiry: str
    card_type: str

class TransactionOut(MongoBase):
    id: str
    amount: float
    type: str
    status: str
    transaction_id: str
    created_at: str

class AuditLogOut(MongoBase):
    id: str
    action: str
    detail: dict
    ip_address: str
    success: bool
    created_at: str

# Transaction / Balance Schema
class TransactionRequest(BaseModel):
    amount: float
    card_id: str  # ID of a saved card (maps to card_token internally)

# Order Schemas
class OrderItemBase(BaseModel):
    product_id: str
    quantity: int

class OrderCreate(BaseModel):
    items: List[OrderItemBase]
    delivery_method: str = "courier"

class OrderItem(MongoBase, OrderItemBase):
    price_at_purchase: float

class Order(MongoBase):
    id: str
    date: datetime
    status: OrderStatus
    total: float
    items: List[OrderItem]

# Category Schemas
class CategoryBase(BaseModel):
    name: str
    icon: str

class CategoryCreate(CategoryBase):
    pass

class Category(MongoBase, CategoryBase):
    id: str

# Auth Response
class Token(BaseModel):
    access_token: str
    token_type: str

# Telegram OTP Schemas
class TelegramOtpRequest(BaseModel):
    telegram_username: str

class TelegramOtpVerify(BaseModel):
    telegram_username: str
    code: str

class TokenData(BaseModel):
    phone: Optional[str] = None

# Contract Schemas
class ContractStatus(str, enum.Enum):
    active = "active"
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"

class PublicUserProfile(MongoBase):
    id: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
    rating: float = 0.0
    review_count: int = 0
    is_online: bool = False
    is_verified: bool = False
    created_at: datetime
    total_orders: int = 0
    successful_orders: int = 0
    unsuccessful_orders: int = 0
    in_progress_orders: int = 0
    reviews: List["ReviewOut"] = []


class ReviewCreate(BaseModel):
    seller_id: str
    order_id: str
    product_id: Optional[str] = None
    rating: int
    comment: str

    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

    @field_validator('comment')
    @classmethod
    def validate_comment(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError('Comment must be at least 10 characters')
        if len(v) > 1000:
            raise ValueError('Comment must be at most 1000 characters')
        return v


class ReviewOut(MongoBase):
    id: str
    reviewer_id: str
    reviewer_name: Optional[str] = None
    seller_id: str
    product_id: Optional[str] = None
    order_id: str
    rating: int
    comment: str
    is_verified_purchase: bool
    created_at: datetime


class FraudReportCreate(BaseModel):
    target_user_id: Optional[str] = None
    target_product_id: Optional[str] = None
    reason: str

    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError('Reason must be at least 10 characters')
        if len(v) > 500:
            raise ValueError('Reason must be at most 500 characters')
        return v


class ContractCreate(BaseModel):
    buyer_id: str
    title: str
    description: Optional[str] = None
    amount: float

class ContractOut(MongoBase):
    id: str
    buyer_id: str
    seller_id: str
    title: str
    description: Optional[str] = None
    amount: float
    status: ContractStatus
    created_at: datetime
    buyer_name: Optional[str] = None
    seller_name: Optional[str] = None

