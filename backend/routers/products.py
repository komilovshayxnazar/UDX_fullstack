from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.encoders import jsonable_encoder
from typing import List, Optional
import uuid
import os

import models
import schemas
from core.dependencies import get_current_user
from core.cache import (
    cache_get, cache_set, cache_delete, cache_delete_pattern,
    CATEGORIES_TTL, PRODUCTS_TTL,
)
from beanie import PydanticObjectId
from beanie.operators import In

router = APIRouter(tags=["products"])

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

@router.post("/upload/image/")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="File must be a JPEG, PNG, WebP, or GIF image")

    contents = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 5 MB")

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join("uploads", unique_filename)

    os.makedirs("uploads", exist_ok=True)
    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    return {"url": f"/uploads/{unique_filename}"}

@router.post("/products/{product_id}/prices/", response_model=schemas.PriceHistory)
async def add_price_history(product_id: str, price_data: schemas.PriceHistoryCreate):
    product = await models.Product.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    new_price = models.PriceHistory(
        product_id=product_id,
        **price_data.model_dump()
    )
    product.price = price_data.price
    await new_price.insert()
    await product.save()
    return new_price

@router.get("/products/{product_id}/prices/", response_model=List[schemas.PriceHistory])
async def get_price_history(product_id: str):
    product = await models.Product.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    prices = await models.PriceHistory.find(models.PriceHistory.product_id == product_id).sort("date").to_list()
    return prices

async def _enrich_with_sellers(products: list) -> List[schemas.Product]:
    """Mahsulotlarga sotuvchi ma'lumotlarini qo'shish (bitta batch so'rov)."""
    seller_ids = list({p.seller_id for p in products if p.seller_id})
    sellers: dict = {}
    if seller_ids:
        valid_ids = [PydanticObjectId(sid) for sid in seller_ids if PydanticObjectId.is_valid(sid)]
        if valid_ids:
            seller_docs = await models.User.find(In(models.User.id, valid_ids)).to_list()
            sellers = {str(s.id): s for s in seller_docs}

    result = []
    for p in products:
        s = sellers.get(p.seller_id)
        seller_pub = schemas.SellerPublic(
            id=str(s.id),
            name=s.name,
            avatar=s.avatar,
            rating=s.rating,
            review_count=s.review_count,
            is_online=s.is_online,
            is_verified=bool(s.tin)
        ) if s else None
        d = {
            "id": str(p.id), "seller_id": p.seller_id, "category_id": p.category_id,
            "name": p.name, "price": p.price, "unit": p.unit, "image": p.image,
            "description": p.description, "in_stock": p.in_stock, "certified": p.certified,
            "is_b2b": p.is_b2b, "rating": p.rating, "review_count": p.review_count,
            "views": p.views, "sales": p.sales, "gallery": p.gallery,
            "seller": seller_pub
        }
        result.append(schemas.Product(**d))
    return result


@router.get("/products/", response_model=List[schemas.Product])
async def read_products(
    skip: int = 0,
    limit: int = 20,
    is_b2b: Optional[bool] = None,
    category_id: Optional[str] = None,
    q: Optional[str] = None
):
    limit = min(limit, 100)
    cache_key = f"products:{skip}:{limit}:{is_b2b}:{category_id}:{q or ''}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    query = models.Product.find_all()
    if is_b2b is not None:
        query = query.find(models.Product.is_b2b == is_b2b)
    if category_id is not None:
        query = query.find(models.Product.category_id == category_id)
    if q and q.strip():
        import re
        regex = re.compile(q.strip(), re.IGNORECASE)
        query = query.find({"name": {"$regex": regex.pattern, "$options": "i"}})
    products = await query.skip(skip).limit(limit).to_list()
    result = await _enrich_with_sellers(products)
    await cache_set(cache_key, jsonable_encoder(result), ttl=PRODUCTS_TTL)
    return result

@router.post("/products/", response_model=schemas.Product)
async def create_product(product: schemas.ProductCreate, current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.UserRole.seller:
         raise HTTPException(status_code=403, detail="Only sellers can create products")

    new_product = models.Product(
        seller_id=str(current_user.id),
        **product.model_dump()
    )
    await new_product.insert()
    await cache_delete_pattern("products:*")
    return new_product

@router.get("/products/{product_id}", response_model=schemas.Product)
async def read_product(product_id: str):
    product = await models.Product.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/products/interactions/")
async def record_interaction(
    interaction: schemas.ProductInteractionCreate,
    current_user: models.User = Depends(get_current_user)
):
    new_interaction = models.ProductInteraction(
        user_id=str(current_user.id),
        **interaction.model_dump()
    )
    await new_interaction.insert()

    # Mirror to Neo4j graph for collaborative filtering (silent if Neo4j is down)
    import asyncio
    from core import neo4j_db as _neo4j
    await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: _neo4j.record_interaction(
            str(current_user.id),
            interaction.product_id,
            interaction.interaction_type.value,
        ),
    )
    return {"status": "ok"}

@router.get("/products/recommendations/", response_model=List[schemas.Product])
async def get_recommendations(limit: int = 10, current_user: models.User = Depends(get_current_user)):
    try:
        from core import ml_recommendations
        from beanie.operators import In
        from beanie import PydanticObjectId
        
        recommended_ids = await ml_recommendations.recommend_for_user(str(current_user.id), limit=limit)
        if recommended_ids:
             valid_ids = [PydanticObjectId(rid) for rid in recommended_ids if PydanticObjectId.is_valid(rid)]
             products = await models.Product.find(In(models.Product.id, valid_ids)).to_list()
             product_map = {str(p.id): p for p in products}
             return await _enrich_with_sellers([product_map[rid] for rid in recommended_ids if rid in product_map])
    except Exception as e:
        print(f"ML Recommendation failed: {e}")
        
    # Fallback: Top products by views
    products = await models.Product.find_all().sort("-views").limit(limit).to_list()
    return await _enrich_with_sellers(products)

@router.get("/categories/", response_model=List[schemas.Category])
async def get_categories():
    cached = await cache_get("categories")
    if cached is not None:
        return cached

    categories = await models.Category.find_all().to_list()
    if not categories:
        from mock_data.seed import CATEGORIES
        for cat_data in CATEGORIES:
            await models.Category(**cat_data).insert()
        categories = await models.Category.find_all().to_list()

    await cache_set("categories", jsonable_encoder(categories), ttl=CATEGORIES_TTL)
    return categories
