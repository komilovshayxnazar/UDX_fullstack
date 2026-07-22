import json
import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
import schemas
from db import get_db
from core.dependencies import get_current_user
from core.errors import E
from services.payment_service import (
    get_idempotency_record,
    save_idempotency_record,
)

router = APIRouter(prefix="/orders", tags=["orders"])


async def _serialize_orders(
    db: AsyncSession, orders: List[models.Order], current_user: models.User
) -> List[schemas.Order]:
    """Attach counterpart name + review status without N+1 queries per order."""
    if not orders:
        return []

    user_id = current_user.id
    counterpart_ids = {
        (o.seller_id if o.buyer_id == user_id else o.buyer_id)
        for o in orders
    }
    counterpart_ids.discard(None)
    names: dict = {}
    if counterpart_ids:
        docs_result = await db.execute(select(models.User).where(models.User.id.in_(counterpart_ids)))
        names = {d.id: d.name for d in docs_result.scalars().all()}

    buyer_order_ids = [o.id for o in orders if o.buyer_id == user_id]
    reviewed_order_ids: set = set()
    if buyer_order_ids:
        reviews_result = await db.execute(
            select(models.Review.order_id).where(
                models.Review.reviewer_id == user_id,
                models.Review.order_id.in_(buyer_order_ids),
            )
        )
        reviewed_order_ids = {r for (r,) in reviews_result.all()}

    result = []
    for o in orders:
        is_buyer = o.buyer_id == user_id
        items = [
            schemas.OrderItem(
                product_id=str(it.product_id) if it.product_id else "",
                quantity=it.quantity,
                price_at_purchase=it.unit_price,
                product_name=it.product_name,
            )
            for it in o.items
        ]
        result.append(schemas.Order(
            id=str(o.id),
            date=o.date,
            status=o.status,
            total=o.total,
            items=items,
            seller_id=str(o.seller_id) if o.seller_id else None,
            seller_name=current_user.name if not is_buyer else names.get(o.seller_id),
            buyer_name=current_user.name if is_buyer else names.get(o.buyer_id),
            is_buyer=is_buyer,
            has_review=o.id in reviewed_order_ids,
        ))
    return result


@router.post("/", response_model=schemas.Order)
async def create_order(
    order: schemas.OrderCreate,
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new order.

    Clients SHOULD pass a unique `X-Idempotency-Key` header per attempt.
    If the same key comes back on retry we return the previously-saved
    order body instead of double-inserting.
    """
    user_id = current_user.id

    # 1. Idempotency short-circuit — replay the previous response if any.
    if idempotency_key:
        existing = await get_idempotency_record(db, idempotency_key, user_id)
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
        try:
            product_id = uuid.UUID(item.product_id)
        except ValueError:
            raise HTTPException(status_code=404, detail=E.PRODUCT_NOT_FOUND)

        product = await db.get(models.Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail=E.PRODUCT_NOT_FOUND)

        if seller_id is None:
            seller_id = product.seller_id
        elif product.seller_id != seller_id:
            raise HTTPException(status_code=400, detail=E.SINGLE_SELLER_CONSTRAINT)

        price = product.b2c_price
        total += price * item.quantity

        db_items.append(models.OrderItem(
            product_id=product.id,
            quantity=item.quantity,
            unit_price=price,
            product_name=product.title,
        ))

    new_order = models.Order(
        buyer_id=user_id,
        seller_id=seller_id,
        total=total,
        status=models.OrderStatus.new,
        delivery_method=models.DeliveryMethod(order.delivery_method),
        items=db_items,
    )
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order, attribute_names=["items"])

    response = (await _serialize_orders(db, [new_order], current_user))[0]

    # 2. Persist the idempotency record so the next retry short-circuits.
    if idempotency_key:
        await save_idempotency_record(db, idempotency_key, user_id, 200, response.model_dump(mode="json"))

    return response


@router.get("/", response_model=List[schemas.Order])
async def read_orders(
    skip: int = 0,
    limit: int = 20,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limit = min(limit, 100)
    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.items))
        .where(or_(models.Order.buyer_id == current_user.id, models.Order.seller_id == current_user.id))
        .order_by(models.Order.date.desc())
        .offset(skip)
        .limit(limit)
    )
    orders = result.scalars().all()
    return await _serialize_orders(db, orders, current_user)


@router.patch("/{order_id}/status", response_model=schemas.Order)
async def update_order_status(
    order_id: str,
    body: schemas.OrderStatusUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        oid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=E.ORDER_NOT_FOUND)

    result = await db.execute(
        select(models.Order).options(selectinload(models.Order.items)).where(models.Order.id == oid)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail=E.ORDER_NOT_FOUND)

    user_id = current_user.id
    is_buyer = order.buyer_id == user_id
    is_seller = order.seller_id == user_id
    if not is_buyer and not is_seller:
        raise HTTPException(status_code=403, detail=E.ORDER_NOT_YOURS)

    current, new_status = order.status, models.OrderStatus(body.status.value)
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

    order.status = new_status
    await db.commit()

    return (await _serialize_orders(db, [order], current_user))[0]
