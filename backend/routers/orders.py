from fastapi import APIRouter, Depends, HTTPException

from typing import List
import uuid

import models
import schemas
from core.dependencies import get_current_user

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=schemas.Order)
async def create_order(order: schemas.OrderCreate, current_user: models.User = Depends(get_current_user)):
    total = 0.0
    db_items = []
    order_id = str(uuid.uuid4())
    seller_id = None
    
    for item in order.items:
        product = await models.Product.get(item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        if seller_id is None:
            seller_id = product.seller_id
        
        price = product.price
        total += price * item.quantity
        
        db_item = models.OrderItem(
            product_id=str(product.id),
            quantity=item.quantity,
            price_at_purchase=price
        )
        db_items.append(db_item)

    new_order = models.Order(
        id=order_id,
        buyer_id=str(current_user.id),
        seller_id=str(seller_id),
        total=total,
        status=models.OrderStatus.new,
        delivery_method=order.delivery_method,
        items=db_items
    )
    
    await new_order.insert()
    return new_order

@router.get("/", response_model=List[schemas.Order])
async def read_orders(skip: int = 0, limit: int = 100, current_user: models.User = Depends(get_current_user)):
    orders = await models.Order.find(
        {"$or": [{"buyer_id": str(current_user.id)}, {"seller_id": str(current_user.id)}]}
    ).skip(skip).limit(limit).to_list()
    return orders
