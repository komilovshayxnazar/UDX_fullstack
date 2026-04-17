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
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from typing import List

import models
import schemas
from core.dependencies import get_current_user
from core.cache import (
    cache_get, cache_set, cache_delete, cache_delete_pattern,
    PROFILE_TTL, REVIEWS_TTL,
)
from beanie import PydanticObjectId
from beanie.operators import In

router = APIRouter(prefix="/reviews", tags=["reviews"])
fraud_router = APIRouter(prefix="/fraud-reports", tags=["fraud"])


# ─── Reviews ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=schemas.ReviewOut)
async def create_review(
    body: schemas.ReviewCreate,
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != models.UserRole.buyer:
        raise HTTPException(status_code=403, detail="Only buyers can leave reviews")

    # Buyurtma mavjud va tugallanganmi?
    order = await models.Order.get(body.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.buyer_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="This order does not belong to you")
    if order.status != models.OrderStatus.completed:
        raise HTTPException(status_code=400, detail="You can only review completed orders")
    if order.seller_id != body.seller_id:
        raise HTTPException(status_code=400, detail="Seller does not match the order")

    # O'z sotuvchisiga sharh qoldirish taqiqlangan
    if body.seller_id == str(current_user.id):
        raise HTTPException(status_code=400, detail="You cannot review yourself")

    # Duplicate tekshiruv (unique index qaytaradi, lekin yaxshi xabar berish uchun)
    existing = await models.Review.find_one(models.Review.order_id == body.order_id)
    if existing:
        raise HTTPException(status_code=409, detail="You already reviewed this order")

    review = models.Review(
        reviewer_id=str(current_user.id),
        seller_id=body.seller_id,
        order_id=body.order_id,
        product_id=body.product_id,
        rating=body.rating,
        comment=body.comment,
        is_verified_purchase=True
    )
    await review.insert()

    # Sotuvchining umumiy ratingini yangilash
    seller = await models.User.get(body.seller_id)
    if seller:
        all_reviews = await models.Review.find(models.Review.seller_id == body.seller_id).to_list()
        seller.review_count = len(all_reviews)
        seller.rating = round(sum(r.rating for r in all_reviews) / len(all_reviews), 2)
        await seller.save()

    # Seller profil va sharhlar cache'ini tozalash
    await cache_delete(f"public_profile:{body.seller_id}")
    await cache_delete_pattern(f"seller_reviews:{body.seller_id}:*")

    return schemas.ReviewOut(
        id=str(review.id),
        reviewer_id=review.reviewer_id,
        reviewer_name=current_user.name,
        seller_id=review.seller_id,
        product_id=review.product_id,
        order_id=review.order_id,
        rating=review.rating,
        comment=review.comment,
        is_verified_purchase=review.is_verified_purchase,
        created_at=review.created_at
    )


@router.get("/seller/{seller_id}", response_model=List[schemas.ReviewOut])
async def get_seller_reviews(seller_id: str, skip: int = 0, limit: int = 20):
    """Sotuvchiga qoldirilgan barcha sharhlar — ommaviy."""
    limit = min(limit, 50)
    cache_key = f"seller_reviews:{seller_id}:{skip}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    reviews = await (
        models.Review.find(models.Review.seller_id == seller_id)
        .sort("-created_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    # N+1 oldini olish: barcha reviewer'larni bitta so'rovda yuklash
    reviewer_ids = list({r.reviewer_id for r in reviews})
    reviewer_names: dict[str, str | None] = {}
    if reviewer_ids:
        valid_ids = [PydanticObjectId(rid) for rid in reviewer_ids if PydanticObjectId.is_valid(rid)]
        if valid_ids:
            docs = await models.User.find(In(models.User.id, valid_ids)).to_list()
            reviewer_names = {str(d.id): d.name for d in docs}

    result = [
        schemas.ReviewOut(
            id=str(r.id),
            reviewer_id=r.reviewer_id,
            reviewer_name=reviewer_names.get(r.reviewer_id),
            seller_id=r.seller_id,
            product_id=r.product_id,
            order_id=r.order_id,
            rating=r.rating,
            comment=r.comment,
            is_verified_purchase=r.is_verified_purchase,
            created_at=r.created_at
        )
        for r in reviews
    ]
    await cache_set(cache_key, jsonable_encoder(result), ttl=REVIEWS_TTL)
    return result


# ─── Fraud Reports ────────────────────────────────────────────────────────────

@fraud_router.post("/")
async def report_fraud(
    body: schemas.FraudReportCreate,
    current_user: models.User = Depends(get_current_user)
):
    if not body.target_user_id and not body.target_product_id:
        raise HTTPException(status_code=400, detail="Specify either target_user_id or target_product_id")

    # Spam himoyasi: bitta target uchun 3 tadan ko'p shikoyat bo'lmasligi kerak
    if body.target_user_id:
        count = await models.FraudReport.find(
            models.FraudReport.reporter_id == str(current_user.id),
            models.FraudReport.target_user_id == body.target_user_id
        ).count()
        if count >= 3:
            raise HTTPException(status_code=429, detail="You have already reported this user multiple times")

    if body.target_product_id:
        count = await models.FraudReport.find(
            models.FraudReport.reporter_id == str(current_user.id),
            models.FraudReport.target_product_id == body.target_product_id
        ).count()
        if count >= 3:
            raise HTTPException(status_code=429, detail="You have already reported this product multiple times")

    report = models.FraudReport(
        reporter_id=str(current_user.id),
        target_user_id=body.target_user_id,
        target_product_id=body.target_product_id,
        reason=body.reason
    )
    await report.insert()
    return {"status": "reported", "message": "Your report has been submitted for review"}
