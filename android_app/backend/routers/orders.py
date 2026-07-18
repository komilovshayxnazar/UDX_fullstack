import json
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException

import models
import schemas
from core.dependencies import get_current_user
from core.errors import E
from services.payment_service import (
    get_idempotency_record,
    save_idempotency_record,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=schemas.Order)
async def create_order(
    order: schemas.OrderCreate,
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    current_user: models.User = Depends(get_current_user),
):
    """
    Create a new order.

    Clients SHOULD pass a unique `X-Idempotency-Key` header per attempt.
    If the same key comes back on retry we return the previously-saved
    order body instead of double-inserting.
    """
    user_id = str(current_user.id)

    # 1. Idempotency short-circuit — replay the previous response if any.
    if idempotency_key:
        existing = await get_idempotency_record(idempotency_key, user_id)
        if existing:
            try:
                return json.loads(existing.response_body)
            except json.JSONDecodeError:
                # Corrupt cached body — fall through and re-execute.
                pass

    total = 0.0
    db_items = []
    seller_id = None

    for item in order.items:
        product = await models.Product.get(item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=E.PRODUCT_NOT_FOUND)

        if seller_id is None:
            seller_id = product.seller_id
        elif str(product.seller_id) != str(seller_id):
            raise HTTPException(status_code=400, detail=E.SINGLE_SELLER_CONSTRAINT)

        price = product.price
        total += price * item.quantity

        db_items.append(models.OrderItem(
            product_id=str(product.id),
            quantity=item.quantity,
            price_at_purchase=price,
        ))

    new_order = models.Order(
        buyer_id=user_id,
        seller_id=str(seller_id),
        total=total,
        status=models.OrderStatus.new,
        delivery_method=order.delivery_method,
        items=db_items,
    )
    await new_order.insert()

    # 2. Persist the idempotency record so the next retry short-circuits.
    if idempotency_key:
        body = schemas.Order.model_validate(new_order, from_attributes=True).model_dump(mode="json")
        await save_idempotency_record(idempotency_key, user_id, 200, body)

    return new_order


@router.get("/", response_model=List[schemas.Order])
async def read_orders(
    skip: int = 0,
    limit: int = 20,
    current_user: models.User = Depends(get_current_user),
):
    limit = min(limit, 100)
    orders = await models.Order.find(
        {"$or": [{"buyer_id": str(current_user.id)}, {"seller_id": str(current_user.id)}]}
    ).skip(skip).limit(limit).to_list()
    return orders
