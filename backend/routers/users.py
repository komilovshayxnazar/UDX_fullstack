import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas
from db import get_db
from core.dependencies import get_current_user
from core.security import get_password_hash, verify_password
from core.encryption import encrypt, decrypt, hmac_hash
from core.cache import cache_get, cache_set, cache_delete, PROFILE_TTL
from core.errors import E
from routers.auth import consume_verified_session, _normalize_phone
from services import wallet_service, payment_service
from services.audit_service import log as audit_log

router = APIRouter(prefix="/users", tags=["users"])


async def _get_card(db: AsyncSession, user_id, card_id: str) -> models.PaymentCard | None:
    try:
        cid = uuid.UUID(card_id)
    except ValueError:
        return None
    result = await db.execute(
        select(models.PaymentCard).where(models.PaymentCard.id == cid, models.PaymentCard.user_id == user_id)
    )
    return result.scalar_one_or_none()


@router.post("/", response_model=schemas.User)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    normalized_phone_pre = _normalize_phone(user.phone)
    ph_pre = hmac_hash(normalized_phone_pre)

    if user.telegram_username:
        if not await consume_verified_session(user.telegram_username):
            raise HTTPException(status_code=400, detail=E.TELEGRAM_OTP_NOT_VERIFIED)
    else:
        if not await consume_verified_session(ph_pre):
            raise HTTPException(status_code=400, detail=E.PHONE_OTP_NOT_VERIFIED)

    normalized_phone = _normalize_phone(user.phone)
    ph = hmac_hash(normalized_phone)
    result = await db.execute(select(models.User).where(models.User.phone_hash == ph))
    db_user = result.scalar_one_or_none()
    if db_user:
        raise HTTPException(status_code=400, detail=E.PHONE_ALREADY_REGISTERED)
    hashed_password = get_password_hash(user.password)
    tg = user.telegram_username.lower().lstrip("@") if user.telegram_username else None
    new_user = models.User(
        phone=encrypt(normalized_phone),
        phone_hash=ph,
        hashed_password=hashed_password,
        role=models.UserRole(user.role.value),
        name=user.name,
        telegram_username=encrypt(tg) if tg else None,
        telegram_username_hash=hmac_hash(tg) if tg else None,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return schemas.user_to_schema(new_user, balance=0.0)

@router.get("/me", response_model=schemas.User)
async def read_users_me(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    balance = await wallet_service.get_balance(db, current_user)
    return schemas.user_to_schema(current_user, balance=balance)


@router.get("/{user_id}/public", response_model=schemas.PublicUserProfile)
async def get_public_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    cache_key = f"public_profile:{user_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=E.USER_NOT_FOUND)

    user = await db.get(models.User, uid)
    if not user or not user.is_public:
        raise HTTPException(status_code=404, detail=E.USER_NOT_FOUND)

    # Savdo statistikasi
    orders_result = await db.execute(select(models.Order).where(models.Order.seller_id == uid))
    orders = orders_result.scalars().all()
    total_orders   = len(orders)
    successful     = sum(1 for o in orders if o.status == models.OrderStatus.completed)
    unsuccessful   = sum(1 for o in orders if o.status == models.OrderStatus.cancelled)
    in_progress    = total_orders - successful - unsuccessful

    # Sharhlar (oxirgi 20 ta)
    reviews_result = await db.execute(
        select(models.Review)
        .where(models.Review.seller_id == uid)
        .order_by(models.Review.created_at.desc())
        .limit(20)
    )
    reviews = reviews_result.scalars().all()
    reviewer_ids = list({r.reviewer_id for r in reviews})
    reviewers: dict = {}
    if reviewer_ids:
        docs_result = await db.execute(select(models.User).where(models.User.id.in_(reviewer_ids)))
        reviewers = {d.id: d.name for d in docs_result.scalars().all()}

    reviews_out = [
        schemas.ReviewOut(
            id=str(r.id), reviewer_id=str(r.reviewer_id),
            reviewer_name=reviewers.get(r.reviewer_id),
            seller_id=str(r.seller_id), product_id=str(r.product_id) if r.product_id else None,
            order_id=str(r.order_id), rating=r.rating, comment=r.comment,
            is_verified_purchase=r.is_verified_purchase, created_at=r.created_at
        ) for r in reviews
    ]

    profile = schemas.PublicUserProfile(
        id=str(user.id), name=user.name, avatar=user.avatar,
        description=user.description, rating=user.rating,
        review_count=user.review_count, is_online=user.is_online,
        is_verified=bool(user.tin),
        created_at=user.created_at,
        total_orders=total_orders, successful_orders=successful,
        unsuccessful_orders=unsuccessful, in_progress_orders=in_progress,
        reviews=reviews_out
    )
    await cache_set(cache_key, jsonable_encoder(profile), ttl=PROFILE_TTL)
    return profile

@router.put("/me", response_model=schemas.User)
async def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_update.name is not None:
        current_user.name = user_update.name
    if user_update.avatar is not None:
        current_user.avatar = user_update.avatar
    if user_update.description is not None:
        current_user.description = user_update.description
    if user_update.is_public is not None:
        current_user.is_public = user_update.is_public

    await db.commit()
    await db.refresh(current_user)
    await cache_delete(f"public_profile:{current_user.id}")
    balance = await wallet_service.get_balance(db, current_user)
    return schemas.user_to_schema(current_user, balance=balance)

@router.put("/me/password")
async def update_password_me(
    password_update: schemas.PasswordUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail=E.OAUTH_NO_PASSWORD)

    if not verify_password(password_update.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail=E.INCORRECT_PASSWORD)

    current_user.hashed_password = get_password_hash(password_update.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}

@router.put("/me/phone")
async def update_phone_me(
    phone_update: schemas.PhoneUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail=E.OAUTH_NO_PASSWORD)

    if not verify_password(phone_update.password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail=E.INCORRECT_PASSWORD)

    new_phone = _normalize_phone(phone_update.new_phone)
    new_ph    = hmac_hash(new_phone)
    result = await db.execute(select(models.User).where(models.User.phone_hash == new_ph))
    existing  = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=E.PHONE_ALREADY_REGISTERED)
    current_user.phone      = encrypt(new_phone)
    current_user.phone_hash = new_ph
    await db.commit()
    return {"message": "Phone updated successfully"}

@router.put("/me/role", response_model=schemas.User)
async def update_role_me(
    role_update: schemas.RoleUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed_roles = {models.UserRole.buyer, models.UserRole.seller}
    new_role = models.UserRole(role_update.role.value)
    if new_role not in allowed_roles:
        raise HTTPException(status_code=403, detail=E.ROLE_FORBIDDEN)
    current_user.role = new_role
    await db.commit()
    balance = await wallet_service.get_balance(db, current_user)
    return schemas.user_to_schema(current_user, balance=balance)

@router.put("/me/2fa", response_model=schemas.User)
async def update_2fa_me(
    two_factor_update: schemas.TwoFactorUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.is_2fa_enabled = two_factor_update.is_2fa_enabled
    await db.commit()
    balance = await wallet_service.get_balance(db, current_user)
    return schemas.user_to_schema(current_user, balance=balance)

@router.get("/me/cards", response_model=list[schemas.PaymentCardOut])
async def get_cards(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(models.PaymentCard).where(models.PaymentCard.user_id == current_user.id))
    cards = result.scalars().all()
    return [
        schemas.PaymentCardOut(
            id=str(c.id), owner_name=c.owner_name, last4=c.last4,
            expiry=c.expiry, card_type=c.card_type,
        )
        for c in cards
    ]

@router.post("/me/cards", response_model=schemas.PaymentCardOut)
async def add_card(
    card: schemas.PaymentCardCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # card_token was issued by the mock/real gateway — full PAN never arrives here.
    new_card = models.PaymentCard(
        user_id=current_user.id,
        owner_name=card.owner_name,
        last4=card.last4,
        expiry=card.expiry,
        card_type=card.card_type,
        card_token=card.card_token,
    )
    db.add(new_card)
    await db.commit()
    await db.refresh(new_card)
    return schemas.PaymentCardOut(
        id=str(new_card.id), owner_name=new_card.owner_name, last4=new_card.last4,
        expiry=new_card.expiry, card_type=new_card.card_type,
    )

@router.delete("/me/cards/{card_id}")
async def delete_card(
    card_id: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    card = await _get_card(db, current_user.id, card_id)
    if card:
        await db.delete(card)
        await db.commit()
    return {"detail": "Card removed"}

@router.post("/me/balance/deposit", response_model=schemas.User)
async def deposit_balance(
    http_request: Request,
    request: schemas.TransactionRequest,
    idempotency_key: str = Header(default=None, alias="X-Idempotency-Key"),
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail=E.AMOUNT_MUST_BE_POSITIVE)
    card = await _get_card(db, current_user.id, request.card_id)
    if not card:
        raise HTTPException(status_code=400, detail=E.CARD_NOT_FOUND)

    if not idempotency_key:
        idempotency_key = str(uuid.uuid4())

    result = await payment_service.charge_card(
        db, user=current_user, card=card, amount=request.amount,
        idempotency_key=idempotency_key, request=http_request
    )
    if result["status"] != "success":
        raise HTTPException(status_code=402, detail=E.PAYMENT_DECLINED)

    # Skip credit on idempotent replay — gateway was not charged again so balance must not increase
    if not result.get("_replay"):
        await wallet_service.credit(
            db, user=current_user, amount=request.amount,
            card_token=card.card_token, idempotency_key=idempotency_key
        )

    balance = await wallet_service.get_balance(db, current_user)
    return schemas.user_to_schema(current_user, balance=balance)

@router.post("/me/balance/withdraw", response_model=schemas.User)
async def withdraw_balance(
    http_request: Request,
    request: schemas.TransactionRequest,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail=E.AMOUNT_MUST_BE_POSITIVE)
    balance = await wallet_service.get_balance(db, current_user)
    if balance < request.amount:
        raise HTTPException(status_code=400, detail=E.INSUFFICIENT_FUNDS)
    card = await _get_card(db, current_user.id, request.card_id)
    if not card:
        raise HTTPException(status_code=400, detail=E.CARD_NOT_FOUND)

    await wallet_service.debit(
        db, user=current_user, amount=request.amount, card_token=card.card_token
    )
    await audit_log(
        db, user=current_user, action=models.AuditAction.withdraw,
        detail={"amount": request.amount, "card_last4": card.last4},
        request=http_request
    )
    balance = await wallet_service.get_balance(db, current_user)
    return schemas.user_to_schema(current_user, balance=balance)
