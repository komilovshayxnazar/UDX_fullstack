from fastapi import APIRouter, Depends, Header, HTTPException, Request
import uuid

import models
import schemas
from core.dependencies import get_current_user
from core.security import get_password_hash, verify_password
from core.encryption import encrypt, decrypt, hmac_hash
from routers.auth import consume_verified_session, _normalize_phone
from services import wallet_service, payment_service
from services.audit_service import log as audit_log

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=schemas.User)
async def create_user(user: schemas.UserCreate):
    # If a telegram_username is provided, require that OTP was verified first
    if user.telegram_username:
        if not consume_verified_session(user.telegram_username):
            raise HTTPException(
                status_code=400,
                detail="Telegram OTP not verified. Please complete the verification step first."
            )

    normalized_phone = _normalize_phone(user.phone)
    ph = hmac_hash(normalized_phone)
    db_user = await models.User.find_one(models.User.phone_hash == ph)
    if db_user:
        raise HTTPException(status_code=400, detail="Phone already registered")
    hashed_password = get_password_hash(user.password)
    tg = user.telegram_username.lower().lstrip("@") if user.telegram_username else None
    new_user = models.User(
        phone=encrypt(normalized_phone),
        phone_hash=ph,
        hashed_password=hashed_password,
        role=user.role,
        name=user.name,
        telegram_username=encrypt(tg) if tg else None,
        telegram_username_hash=hmac_hash(tg) if tg else None,
    )
    await new_user.insert()
    return schemas.user_to_schema(new_user)

@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return schemas.user_to_schema(current_user)


@router.get("/{user_id}/public", response_model=schemas.PublicUserProfile)
async def get_public_profile(user_id: str):
    user = await models.User.get(user_id)
    if not user or not user.is_public:
        raise HTTPException(status_code=404, detail="User not found or profile is private")

    # Savdo statistikasi
    orders = await models.Order.find(models.Order.seller_id == user_id).to_list()
    total_orders   = len(orders)
    successful     = sum(1 for o in orders if o.status == models.OrderStatus.completed)
    unsuccessful   = sum(1 for o in orders if o.status == models.OrderStatus.cancelled)
    in_progress    = total_orders - successful - unsuccessful

    # Sharhlar (oxirgi 20 ta)
    reviews = await (
        models.Review.find(models.Review.seller_id == user_id)
        .sort("-created_at").limit(20).to_list()
    )
    reviewer_ids = list({r.reviewer_id for r in reviews})
    reviewers = {}
    if reviewer_ids:
        from beanie import PydanticObjectId
        from beanie.operators import In
        docs = await models.User.find(
            In(models.User.id, [PydanticObjectId(rid) for rid in reviewer_ids if PydanticObjectId.is_valid(rid)])
        ).to_list()
        reviewers = {str(d.id): d.name for d in docs}

    reviews_out = [
        schemas.ReviewOut(
            id=str(r.id), reviewer_id=r.reviewer_id,
            reviewer_name=reviewers.get(r.reviewer_id),
            seller_id=r.seller_id, product_id=r.product_id,
            order_id=r.order_id, rating=r.rating, comment=r.comment,
            is_verified_purchase=r.is_verified_purchase, created_at=r.created_at
        ) for r in reviews
    ]

    return schemas.PublicUserProfile(
        id=str(user.id), name=user.name, avatar=user.avatar,
        description=user.description, rating=user.rating,
        review_count=user.review_count, is_online=user.is_online,
        is_verified=bool(user.tin),
        created_at=user.created_at,
        total_orders=total_orders, successful_orders=successful,
        unsuccessful_orders=unsuccessful, in_progress_orders=in_progress,
        reviews=reviews_out
    )

@router.put("/me", response_model=schemas.User)
async def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user)
):
    if user_update.name is not None:
        current_user.name = user_update.name
    if user_update.avatar is not None:
        current_user.avatar = user_update.avatar
    if user_update.description is not None:
        current_user.description = user_update.description
    if user_update.is_public is not None:
        current_user.is_public = user_update.is_public
        
    await current_user.save()
    return schemas.user_to_schema(current_user)

@router.put("/me/password")
async def update_password_me(
    password_update: schemas.PasswordUpdate,
    current_user: models.User = Depends(get_current_user)
):
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="Cannot change password for OAuth users")
    
    if not verify_password(password_update.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
        
    current_user.hashed_password = get_password_hash(password_update.new_password)
    await current_user.save()
    return {"message": "Password updated successfully"}

@router.put("/me/phone")
async def update_phone_me(
    phone_update: schemas.PhoneUpdate,
    current_user: models.User = Depends(get_current_user)
):
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="Cannot change phone for OAuth users")
    
    if not verify_password(phone_update.password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
        
    new_phone = _normalize_phone(phone_update.new_phone)
    new_ph    = hmac_hash(new_phone)
    existing  = await models.User.find_one(models.User.phone_hash == new_ph)
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    current_user.phone      = encrypt(new_phone)
    current_user.phone_hash = new_ph
    await current_user.save()
    return {"message": "Phone updated successfully"}

@router.put("/me/role", response_model=schemas.User)
async def update_role_me(
    role_update: schemas.RoleUpdate,
    current_user: models.User = Depends(get_current_user)
):
    allowed_roles = {models.UserRole.buyer, models.UserRole.seller}
    if role_update.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Cannot assign this role")
    current_user.role = role_update.role
    await current_user.save()
    return schemas.user_to_schema(current_user)

@router.put("/me/2fa", response_model=schemas.User)
async def update_2fa_me(
    two_factor_update: schemas.TwoFactorUpdate,
    current_user: models.User = Depends(get_current_user)
):
    current_user.is_2fa_enabled = two_factor_update.is_2fa_enabled
    await current_user.save()
    return schemas.user_to_schema(current_user)

@router.get("/me/cards", response_model=list[schemas.PaymentCardOut])
async def get_cards(current_user: models.User = Depends(get_current_user)):
    return current_user.payment_cards

@router.post("/me/cards", response_model=schemas.PaymentCardOut)
async def add_card(
    card: schemas.PaymentCardCreate,
    current_user: models.User = Depends(get_current_user)
):
    # card_token was issued by the mock/real gateway — full PAN never arrives here.
    new_card = models.PaymentCard(
        id=str(uuid.uuid4()),
        owner_name=card.owner_name,
        last4=card.last4,
        expiry=card.expiry,
        card_type=card.card_type,
        card_token=card.card_token
    )
    current_user.payment_cards.append(new_card)
    await current_user.save()
    return new_card

@router.delete("/me/cards/{card_id}")
async def delete_card(
    card_id: str,
    current_user: models.User = Depends(get_current_user)
):
    current_user.payment_cards = [c for c in current_user.payment_cards if c.id != card_id]
    await current_user.save()
    return {"detail": "Card removed"}

@router.post("/me/balance/deposit", response_model=schemas.User)
async def deposit_balance(
    http_request: Request,
    request: schemas.TransactionRequest,
    idempotency_key: str = Header(default=None, alias="X-Idempotency-Key"),
    current_user: models.User = Depends(get_current_user)
):
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    card = next((c for c in current_user.payment_cards if c.id == request.card_id), None)
    if not card:
        raise HTTPException(status_code=400, detail="Card not found. Please add a payment card first.")

    if not idempotency_key:
        idempotency_key = str(uuid.uuid4())

    result = await payment_service.charge_card(
        user=current_user, card=card, amount=request.amount,
        idempotency_key=idempotency_key, request=http_request
    )
    if result["status"] != "success":
        raise HTTPException(status_code=402, detail="Payment gateway declined the charge.")

    # Skip credit on idempotent replay — gateway was not charged again so balance must not increase
    if not result.get("_replay"):
        await wallet_service.credit(
            user=current_user, amount=request.amount,
            card_token=card.card_token, idempotency_key=idempotency_key
        )

    user = await models.User.get(current_user.id)
    return schemas.user_to_schema(user)

@router.post("/me/balance/withdraw", response_model=schemas.User)
async def withdraw_balance(
    http_request: Request,
    request: schemas.TransactionRequest,
    current_user: models.User = Depends(get_current_user)
):
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if current_user.balance < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    card = next((c for c in current_user.payment_cards if c.id == request.card_id), None)
    if not card:
        raise HTTPException(status_code=400, detail="Card not found. Please add a payment card first.")

    await wallet_service.debit(
        user=current_user, amount=request.amount, card_token=card.card_token
    )
    await audit_log(
        user=current_user, action=models.AuditAction.withdraw,
        detail={"amount": request.amount, "card_last4": card.last4},
        request=http_request
    )
    return schemas.user_to_schema(current_user)
