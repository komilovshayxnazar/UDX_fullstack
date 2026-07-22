import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.encoders import jsonable_encoder
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas
from db import get_db
from core.dependencies import get_current_user
from core.cache import (
    cache_get, cache_set, cache_delete, cache_delete_pattern,
    CATEGORIES_TTL, PRODUCTS_TTL,
)
from core.errors import E
from core.storage import upload_file

router = APIRouter(tags=["products"])

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Fayl magic bytes — content-type spoofing'dan himoya
_MAGIC: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff",       "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n",  "image/png"),
    (b"GIF87a",             "image/gif"),
    (b"GIF89a",             "image/gif"),
    (b"RIFF",               "image/webp"),   # + bytes[8:12] == b"WEBP"
]


def _detect_image_type(data: bytes) -> str | None:
    for magic, mime in _MAGIC:
        if data[:len(magic)] == magic:
            if mime == "image/webp" and data[8:12] != b"WEBP":
                continue
            return mime
    return None


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


@router.post("/upload/image/")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=E.INVALID_IMAGE_TYPE)

    contents = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=E.FILE_TOO_LARGE)

    # Magic bytes tekshiruvi — content-type header soxtalashtirish mumkin emas
    real_type = _detect_image_type(contents)
    if real_type is None or real_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=E.INVALID_IMAGE_TYPE)

    url = await upload_file(contents, file.filename or "image", real_type)
    return {"url": url}

@router.post("/products/{product_id}/prices/", response_model=schemas.PriceHistory)
async def add_price_history(
    product_id: str,
    price_data: schemas.PriceHistoryCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pid = _parse_uuid(product_id)
    if pid is None:
        raise HTTPException(status_code=404, detail=E.PRODUCT_NOT_FOUND)

    product = await db.get(models.Product, pid)
    if not product:
        raise HTTPException(status_code=404, detail=E.PRODUCT_NOT_FOUND)

    # Only the seller who owns the product can rewrite its price / add a
    # history point. Otherwise an anonymous caller could overwrite
    # any product's price.
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail=E.SELLER_ONLY)

    new_price = models.PriceHistory(
        product_id=pid,
        price=price_data.price,
    )
    product.b2c_price = price_data.price
    db.add(new_price)
    await db.commit()
    await db.refresh(new_price)
    await cache_delete_pattern("products:*")
    return schemas.PriceHistory(
        id=str(new_price.id), product_id=str(new_price.product_id),
        price=new_price.price, date=new_price.changed_at,
    )

@router.get("/products/{product_id}/prices/", response_model=List[schemas.PriceHistory])
async def get_price_history(product_id: str, db: AsyncSession = Depends(get_db)):
    pid = _parse_uuid(product_id)
    if pid is None:
        raise HTTPException(status_code=404, detail=E.PRODUCT_NOT_FOUND)

    product = await db.get(models.Product, pid)
    if not product:
        raise HTTPException(status_code=404, detail=E.PRODUCT_NOT_FOUND)

    result = await db.execute(
        select(models.PriceHistory)
        .where(models.PriceHistory.product_id == pid)
        .order_by(models.PriceHistory.changed_at.asc())
    )
    prices = result.scalars().all()
    return [
        schemas.PriceHistory(id=str(p.id), product_id=str(p.product_id), price=p.price, date=p.changed_at)
        for p in prices
    ]


def _to_product_schema(p: models.Product, seller: Optional[models.User]) -> schemas.Product:
    seller_pub = schemas.SellerPublic(
        id=str(seller.id),
        name=seller.name,
        avatar=seller.avatar,
        rating=seller.rating,
        review_count=seller.review_count,
        is_online=seller.is_online,
        is_verified=bool(seller.tin)
    ) if seller else None
    return schemas.Product(
        id=str(p.id), seller_id=str(p.seller_id), category_id=str(p.category_id),
        name=p.title, price=p.b2c_price, unit=p.unit, image=p.image,
        description=p.description, in_stock=p.stock > 0, certified=p.certified,
        is_b2b=p.is_b2b, rating=p.rating, review_count=p.review_count,
        views=p.views, sales=p.sales, gallery=p.gallery or [],
        region=p.region, seller=seller_pub,
    )


async def _enrich_with_sellers(db: AsyncSession, products: list) -> List[schemas.Product]:
    """Mahsulotlarga sotuvchi ma'lumotlarini qo'shish (bitta batch so'rov)."""
    seller_ids = list({p.seller_id for p in products if p.seller_id})
    sellers: dict = {}
    if seller_ids:
        seller_docs_result = await db.execute(select(models.User).where(models.User.id.in_(seller_ids)))
        sellers = {s.id: s for s in seller_docs_result.scalars().all()}

    return [_to_product_schema(p, sellers.get(p.seller_id)) for p in products]


@router.get("/products/", response_model=List[schemas.Product])
async def read_products(
    skip: int = 0,
    limit: int = 20,
    is_b2b: Optional[bool] = None,
    category_id: Optional[str] = None,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    limit = min(limit, 100)
    cache_key = f"products:{skip}:{limit}:{is_b2b}:{category_id}:{q or ''}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    stmt = select(models.Product)
    if is_b2b is not None:
        stmt = stmt.where(models.Product.is_b2b == is_b2b)
    if category_id is not None:
        cid = _parse_uuid(category_id)
        stmt = stmt.where(models.Product.category_id == cid) if cid else stmt.where(False)
    if q and q.strip():
        # Escape user input so an attacker can't submit a pathological
        # pattern that DoS-es the database (ReDoS). Also caps pattern length.
        pattern = f"%{re.escape(q.strip()[:100])}%"
        stmt = stmt.where(models.Product.title.ilike(pattern))
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    products = result.scalars().all()
    result_list = await _enrich_with_sellers(db, products)
    await cache_set(cache_key, jsonable_encoder(result_list), ttl=PRODUCTS_TTL)
    return result_list

@router.post("/products/", response_model=schemas.Product)
async def create_product(
    product: schemas.ProductCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != models.UserRole.seller:
        raise HTTPException(status_code=403, detail=E.SELLER_ONLY)

    cid = _parse_uuid(product.category_id)
    if cid is None:
        raise HTTPException(status_code=400, detail=E.PRODUCT_NOT_FOUND)

    new_product = models.Product(
        seller_id=current_user.id,
        category_id=cid,
        title=product.name,
        b2c_price=product.price,
        unit=product.unit,
        image=product.image,
        description=product.description,
        stock=100 if product.in_stock else 0,
        certified=product.certified,
        is_b2b=product.is_b2b,
        gallery=product.gallery,
        region=product.region,
    )
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    await cache_delete_pattern("products:*")
    return _to_product_schema(new_product, current_user)

@router.get("/products/{product_id}", response_model=schemas.Product)
async def read_product(product_id: str, db: AsyncSession = Depends(get_db)):
    pid = _parse_uuid(product_id)
    if pid is None:
        raise HTTPException(status_code=404, detail=E.PRODUCT_NOT_FOUND)
    product = await db.get(models.Product, pid)
    if product is None:
        raise HTTPException(status_code=404, detail=E.PRODUCT_NOT_FOUND)
    seller = await db.get(models.User, product.seller_id) if product.seller_id else None
    return _to_product_schema(product, seller)

@router.post("/products/interactions/")
async def record_interaction(
    interaction: schemas.ProductInteractionCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pid = _parse_uuid(interaction.product_id)
    if pid is None:
        raise HTTPException(status_code=404, detail=E.PRODUCT_NOT_FOUND)

    new_interaction = models.ProductInteraction(
        user_id=current_user.id,
        product_id=pid,
        interaction_type=models.InteractionType(interaction.interaction_type.value),
    )
    db.add(new_interaction)
    await db.commit()
    return {"status": "ok"}

@router.get("/products/recommendations/", response_model=List[schemas.Product])
async def get_recommendations(
    limit: int = 10,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        from core import ml_recommendations

        recommended_ids = await ml_recommendations.recommend_for_user(db, str(current_user.id), limit=limit)
        if recommended_ids:
            valid_ids = [_parse_uuid(rid) for rid in recommended_ids]
            valid_ids = [rid for rid in valid_ids if rid is not None]
            if valid_ids:
                products_result = await db.execute(select(models.Product).where(models.Product.id.in_(valid_ids)))
                product_map = {p.id: p for p in products_result.scalars().all()}
                ordered = [product_map[uuid.UUID(rid)] for rid in recommended_ids
                           if _parse_uuid(rid) in product_map]
                if ordered:
                    return await _enrich_with_sellers(db, ordered)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("ML recommendation failed: %s", e)

    # Fallback: Top products by views
    result = await db.execute(select(models.Product).order_by(models.Product.views.desc()).limit(limit))
    products = result.scalars().all()
    return await _enrich_with_sellers(db, products)

@router.get("/categories/", response_model=List[schemas.Category])
async def get_categories(db: AsyncSession = Depends(get_db)):
    cached = await cache_get("categories")
    if cached is not None:
        return cached

    result = await db.execute(select(models.Category))
    categories = result.scalars().all()
    if not categories:
        from mock_data.seed import CATEGORIES
        for cat_data in CATEGORIES:
            db.add(models.Category(**cat_data))
        await db.commit()
        result = await db.execute(select(models.Category))
        categories = result.scalars().all()

    out = [schemas.Category(id=str(c.id), name=c.name, icon=c.icon) for c in categories]
    await cache_set("categories", jsonable_encoder(out), ttl=CATEGORIES_TTL)
    return out
