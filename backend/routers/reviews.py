"""
Sharh va firibgarlikdan himoya tizimi.

Anti-fraud qoidalari:
  - Faqat role=buyer sharh qoldira oladi
  - Sharh faqat TUGALLANGAN (completed) buyurtma bo'yicha yoziladi
  - Har bir buyurtma uchun faqat 1 ta sharh (unique index order_id)
  - O'z mahsulotiga sharh qoldirish taqiqlangan
  - FraudReport: har qanday foydalanuvchi sotuvchini yoki mahsulotni shikoyat qila oladi
  - Shikoyat spam'ini oldini olish: 1 ta target uchun maksimal 3 ta shikoyat
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas
from db import get_db
from core.dependencies import get_current_user
from core.cache import (
    cache_get, cache_set, cache_delete, cache_delete_pattern,
    PROFILE_TTL, REVIEWS_TTL,
)
from core.errors import E

router = APIRouter(prefix="/reviews", tags=["reviews"])
fraud_router = APIRouter(prefix="/fraud-reports", tags=["fraud"])


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


# ─── Reviews ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=schemas.ReviewOut)
async def create_review(
    body: schemas.ReviewCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != models.UserRole.buyer:
        raise HTTPException(status_code=403, detail=E.BUYER_ONLY_REVIEWS)

    order_id = _parse_uuid(body.order_id)
    seller_id = _parse_uuid(body.seller_id)
    if order_id is None or seller_id is None:
        raise HTTPException(status_code=404, detail=E.ORDER_NOT_FOUND)

    order = await db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail=E.ORDER_NOT_FOUND)
    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail=E.ORDER_NOT_YOURS)
    if order.status != models.OrderStatus.completed:
        raise HTTPException(status_code=400, detail=E.COMPLETED_ORDERS_ONLY)
    if order.seller_id != seller_id:
        raise HTTPException(status_code=400, detail=E.SELLER_MISMATCH)

    if seller_id == current_user.id:
        raise HTTPException(status_code=400, detail=E.SELF_REVIEW_FORBIDDEN)

    existing_result = await db.execute(select(models.Review).where(models.Review.order_id == order_id))
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=E.REVIEW_ALREADY_EXISTS)

    # reviews.product_id is NOT NULL — a review must reference a real product.
    product_id = _parse_uuid(body.product_id)
    if product_id is None:
        raise HTTPException(status_code=400, detail=E.PRODUCT_NOT_FOUND)
    product = await db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail=E.PRODUCT_NOT_FOUND)

    review = models.Review(
        reviewer_id=current_user.id,
        seller_id=seller_id,
        order_id=order_id,
        product_id=product_id,
        rating=body.rating,
        comment=body.comment,
        is_verified_purchase=True
    )
    db.add(review)
    await db.flush()

    # Sotuvchining umumiy ratingini yangilash
    seller = await db.get(models.User, seller_id)
    if seller:
        all_reviews_result = await db.execute(select(models.Review).where(models.Review.seller_id == seller_id))
        all_reviews = all_reviews_result.scalars().all()
        seller.review_count = len(all_reviews)
        seller.rating = round(sum(r.rating for r in all_reviews) / len(all_reviews), 2)

    await db.commit()
    await db.refresh(review)

    # Seller profil va sharhlar cache'ini tozalash
    await cache_delete(f"public_profile:{seller_id}")
    await cache_delete_pattern(f"seller_reviews:{seller_id}:*")

    return schemas.ReviewOut(
        id=str(review.id),
        reviewer_id=str(review.reviewer_id),
        reviewer_name=current_user.name,
        seller_id=str(review.seller_id),
        product_id=str(review.product_id) if review.product_id else None,
        order_id=str(review.order_id),
        rating=review.rating,
        comment=review.comment,
        is_verified_purchase=review.is_verified_purchase,
        created_at=review.created_at
    )


@router.get("/seller/{seller_id}", response_model=List[schemas.ReviewOut])
async def get_seller_reviews(
    seller_id: str, skip: int = 0, limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Sotuvchiga qoldirilgan barcha sharhlar — ommaviy."""
    limit = min(limit, 50)
    cache_key = f"seller_reviews:{seller_id}:{skip}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    sid = _parse_uuid(seller_id)
    if sid is None:
        return []

    result = await db.execute(
        select(models.Review)
        .where(models.Review.seller_id == sid)
        .order_by(models.Review.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    reviews = result.scalars().all()

    # N+1 oldini olish: barcha reviewer'larni bitta so'rovda yuklash
    reviewer_ids = list({r.reviewer_id for r in reviews})
    reviewer_names: dict = {}
    if reviewer_ids:
        docs_result = await db.execute(select(models.User).where(models.User.id.in_(reviewer_ids)))
        reviewer_names = {d.id: d.name for d in docs_result.scalars().all()}

    result_list = [
        schemas.ReviewOut(
            id=str(r.id),
            reviewer_id=str(r.reviewer_id),
            reviewer_name=reviewer_names.get(r.reviewer_id),
            seller_id=str(r.seller_id),
            product_id=str(r.product_id) if r.product_id else None,
            order_id=str(r.order_id),
            rating=r.rating,
            comment=r.comment,
            is_verified_purchase=r.is_verified_purchase,
            created_at=r.created_at
        )
        for r in reviews
    ]
    await cache_set(cache_key, jsonable_encoder(result_list), ttl=REVIEWS_TTL)
    return result_list


# ─── Fraud Reports ────────────────────────────────────────────────────────────

@fraud_router.post("/")
async def report_fraud(
    body: schemas.FraudReportCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.target_user_id and not body.target_product_id:
        raise HTTPException(status_code=400, detail=E.SPECIFY_REPORT_TARGET)

    target_user_id = _parse_uuid(body.target_user_id)
    target_product_id = _parse_uuid(body.target_product_id)

    if body.target_user_id and target_user_id:
        count_result = await db.execute(
            select(func.count()).select_from(models.FraudReport).where(
                models.FraudReport.reporter_id == current_user.id,
                models.FraudReport.reported_user_id == target_user_id,
            )
        )
        if count_result.scalar_one() >= 3:
            raise HTTPException(status_code=429, detail=E.USER_REPORT_LIMIT)

    if body.target_product_id and target_product_id:
        count_result = await db.execute(
            select(func.count()).select_from(models.FraudReport).where(
                models.FraudReport.reporter_id == current_user.id,
                models.FraudReport.reported_product_id == target_product_id,
            )
        )
        if count_result.scalar_one() >= 3:
            raise HTTPException(status_code=429, detail=E.PRODUCT_REPORT_LIMIT)

    report = models.FraudReport(
        reporter_id=current_user.id,
        reported_user_id=target_user_id,
        reported_product_id=target_product_id,
        reason=body.reason,
        status="pending",
    )
    db.add(report)
    await db.commit()
    return {"status": "reported", "message": "Your report has been submitted for review"}
