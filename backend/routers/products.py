from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List, Optional
import uuid
import os
import shutil

import models
import schemas
from core.dependencies import get_current_user

router = APIRouter(tags=["products"])

@router.post("/upload/image/")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join("uploads", unique_filename)
    
    os.makedirs("uploads", exist_ok=True)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"url": f"/uploads/{unique_filename}"}

@router.post("/products/{product_id}/prices/", response_model=schemas.PriceHistory)
async def add_price_history(product_id: str, price_data: schemas.PriceHistoryCreate):
    product = await models.Product.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    new_price = models.PriceHistory(
        id=str(uuid.uuid4()),
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

@router.get("/products/", response_model=List[schemas.Product])
async def read_products(
    skip: int = 0, 
    limit: int = 100, 
    is_b2b: Optional[bool] = None,
    category_id: Optional[str] = None
):
    query = models.Product.find_all()
    if is_b2b is not None:
        query = query.find(models.Product.is_b2b == is_b2b)
    if category_id is not None:
        query = query.find(models.Product.category_id == category_id)
        
    products = await query.skip(skip).limit(limit).to_list()
    return products

@router.post("/products/", response_model=schemas.Product)
async def create_product(product: schemas.ProductCreate, current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.UserRole.seller:
         raise HTTPException(status_code=403, detail="Only sellers can create products")
         
    new_product = models.Product(
        id=str(uuid.uuid4()),
        seller_id=current_user.id,
        **product.dict()
    )
    await new_product.insert()
    return new_product

@router.get("/products/{product_id}", response_model=schemas.Product)
async def read_product(product_id: str):
    product = await models.Product.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/products/interactions/")
async def record_interaction(interaction: schemas.ProductInteractionCreate, current_user: models.User = Depends(get_current_user)):
    new_interaction = models.ProductInteraction(
        user_id=current_user.id,
        **interaction.model_dump()
    )
    await new_interaction.insert()
    return {"status": "ok"}

@router.get("/products/recommendations/", response_model=List[schemas.Product])
async def get_recommendations(limit: int = 10, current_user: models.User = Depends(get_current_user)):
    try:
        from core import ml_recommendations
        from beanie.operators import In
        from beanie import PydanticObjectId
        
        recommended_ids = ml_recommendations.recommend_for_user(str(current_user.id), limit=limit)
        if recommended_ids:
             valid_ids = [PydanticObjectId(rid) for rid in recommended_ids if PydanticObjectId.is_valid(rid)]
             products = await models.Product.find(In(models.Product.id, valid_ids)).to_list()
             product_map = {str(p.id): p for p in products}
             return [product_map[rid] for rid in recommended_ids if rid in product_map]
    except Exception as e:
        print(f"ML Recommendation failed: {e}")
        
    # Fallback: Top products by views
    return await models.Product.find_all().sort("-views").limit(limit).to_list()

@router.get("/categories/", response_model=List[schemas.Category])
async def get_categories():
    categories = await models.Category.find_all().to_list()
    if not categories:
        # Seed initial categories if none exist
        initial_categories = [
            {"name": "Fruit", "icon": "🍎"},
            {"name": "Vegetables", "icon": "🥕"},
            {"name": "Dairy", "icon": "🥛"},
            {"name": "Grain", "icon": "🌾"},
            {"name": "Meat", "icon": "🥩"}
        ]
        for cat_data in initial_categories:
            new_cat = models.Category(
                id=str(uuid.uuid4()),
                **cat_data
            )
            await new_cat.insert()
        categories = await models.Category.find_all().to_list()
    return categories
