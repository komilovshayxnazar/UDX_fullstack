import json
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from beanie import PydanticObjectId
from beanie.operators import In

import models
import schemas
from core.dependencies import get_current_user
from core.errors import E
from services.payment_service import (
    get_idempotency_record,
    save_idempotency_record,
)

router = APIRouter(prefix="/orders", tags=["orders"])


async def _serialize_orders(orders: List[models.Order], current_user: models.User) -> List[schemas.Order]:
    """Attach counterpart name + review status without N+1 queries per order."""
    if not orders:
        return []

    user_id = str(current_user.id)
    counterpart_ids = {
        (o.seller_id if o.buyer_id == user_id else o.buyer_id)
        for o in orders
    }
    counterpart_ids.discard(None)
    valid_ids = [PydanticObjectId(i) for i in counterpart_ids if PydanticObjectId.is_valid(i)]
    names: dict[str, str | None] = {}
    if valid_ids:
        docs = await models.User.find(In(models.User.id, valid_ids)).to_list()
        names = {str(d.id): d.name for d in docs}

    buyer_order_ids = [str(o.id) for o in orders if o.buyer_id == user_id]
    reviewed_order_ids: set[str] = set()
    if buyer_order_ids:
        reviews = await models.Review.find(
            models.Review.reviewer_id == user_id,
            In(models.Review.order_id, buyer_order_ids),
        ).to_list()
        reviewed_order_ids = {r.order_id for r in reviews}

    result = []
    for o in orders:
        is_buyer = o.buyer_id == user_id
        result.append(schemas.Order(
            id=str(o.id),
            date=o.date,
            status=o.status,
            total=o.total,
            items=o.items,
            seller_id=o.seller_id,
            seller_name=current_user.name if not is_buyer else names.get(o.seller_id),
            buyer_name=current_user.name if is_buyer else names.get(o.buyer_id),
            is_buyer=is_buyer,
            has_review=str(o.id) in reviewed_order_ids,
        ))
    return result


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
            product_name=product.name,
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

    response = (await _serialize_orders([new_order], current_user))[0]

    # 2. Persist the idempotency record so the next retry short-circuits.
    if idempotency_key:
        await save_idempotency_record(idempotency_key, user_id, 200, response.model_dump(mode="json"))

    return response


@router.get("/", response_model=List[schemas.Order])
async def read_orders(
    skip: int = 0,
    limit: int = 20,
    current_user: models.User = Depends(get_current_user),
):
    limit = min(limit, 100)
    orders = await models.Order.find(
        {"$or": [{"buyer_id": str(current_user.id)}, {"seller_id": str(current_user.id)}]}
    ).sort("-date").skip(skip).limit(limit).to_list()
    return await _serialize_orders(orders, current_user)


@router.patch("/{order_id}/status", response_model=schemas.Order)
async def update_order_status(
    order_id: str,
    body: schemas.OrderStatusUpdate,
    current_user: models.User = Depends(get_current_user),
):
    order = await models.Order.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=E.ORDER_NOT_FOUND)

    user_id = str(current_user.id)
    is_buyer = order.buyer_id == user_id
    is_seller = order.seller_id == user_id
    if not is_buyer and not is_seller:
        raise HTTPException(status_code=403, detail=E.ORDER_NOT_YOURS)

    current, new_status = order.status, body.status
    allowed = (
        (is_seller and current == models.OrderStatus.new and new_status == models.OrderStatus.in_process)
        or (is_seller and current == models.OrderStatus.in_process and new_status == models.OrderStatus.completed)
        or (
            new_status == models.OrderStatus.cancelled
            and current in (models.OrderStatus.new, models.OrderStatus.in_process)
        )
    )
    if not allowed:
        raise HTTPException(status_code=400, detail=E.ORDER_STATUS_INVALID_TRANSITION)

    order.status = models.OrderStatus(new_status.value)
    await order.save()

    return (await _serialize_orders([order], current_user))[0]
