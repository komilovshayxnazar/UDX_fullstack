"""
routers/dev.py — Development / debug endpoints only.

Mounted from main.py only when ENVIRONMENT != "production". As a
defense-in-depth measure the destructive endpoints below also require
a shared-secret admin token (DEV_ADMIN_TOKEN) passed as the
`X-Dev-Admin-Token` header, so a mistakenly mounted router still
cannot wipe the database from the public internet.
"""

import os
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas
from db import get_db
from core.encryption import hmac_hash
from mock_data.seed import run_seed
import telegram_bot
from routers.auth import _session_set, _normalize_phone

router = APIRouter(prefix="/dev", tags=["dev"])


def _require_dev_admin(x_dev_admin_token: str | None = Header(default=None)) -> None:
    """Reject dev-router calls unless the shared admin token is presented."""
    expected = os.getenv("DEV_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dev endpoints disabled: DEV_ADMIN_TOKEN is not set",
        )
    if not x_dev_admin_token or x_dev_admin_token != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev endpoints require X-Dev-Admin-Token header",
        )


@router.get("/telegram/status")
async def telegram_status(username: str = ""):
    """Bot holati va username /start yuborganmi tekshiradi."""
    token_set  = bool(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    bot_running = telegram_bot._app is not None
    chat_id     = telegram_bot.get_chat_id(username) if username else None
    return {
        "token_configured":    token_set,
        "bot_running":         bot_running,
        "username_registered": chat_id is not None,
        "chat_id":             chat_id,
    }


@router.post("/verify-phone", dependencies=[Depends(_require_dev_admin)])
async def dev_verify_phone(phone: str):
    """Test uchun — OTP tasdiqlamasdan telefon raqamni verified qilib belgilaydi."""
    ph = hmac_hash(_normalize_phone(phone))
    await _session_set(ph)
    return {"verified": True, "phone": phone}


@router.post("/seed", dependencies=[Depends(_require_dev_admin)])
async def seed_data(db: AsyncSession = Depends(get_db)):
    """Mock ma'lumotlarni bazaga yozadi (agar mavjud bo'lmasa)."""
    return await run_seed(db)


@router.post("/reset-seed", dependencies=[Depends(_require_dev_admin)])
async def reset_and_seed(db: AsyncSession = Depends(get_db)):
    """Barcha test ma'lumotlarini o'chirib qayta seed qiladi."""
    # Delete in FK-safe order (children before parents).
    for cls in [
        models.Review, models.FraudReport, models.OrderItem, models.Order,
        models.PriceHistory, models.Product, models.Category, models.User,
    ]:
        await db.execute(delete(cls))
    await db.commit()
    return await run_seed(db)


@router.post("/sync-categories", dependencies=[Depends(_require_dev_admin)])
async def sync_categories(db: AsyncSession = Depends(get_db)):
    """Bazada yo'q kategoriyalarni qo'shadi (mavjudlarini o'zgartirmaydi)."""
    from mock_data.seed import CATEGORIES
    added = []
    for cat in CATEGORIES:
        result = await db.execute(select(models.Category).where(models.Category.name == cat["name"]))
        exists = result.scalar_one_or_none()
        if not exists:
            db.add(models.Category(**cat))
            added.append(cat["name"])
    await db.commit()
    count_result = await db.execute(select(func.count()).select_from(models.Category))
    return {"added": added, "total": count_result.scalar_one()}


@router.post("/orders/{order_id}/complete", dependencies=[Depends(_require_dev_admin)])
async def dev_complete_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Test uchun — order statusini completed ga o'zgartiradi."""
    try:
        oid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found")
    order = await db.get(models.Order, oid)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = models.OrderStatus.completed
    await db.commit()
    return {"status": "completed", "order_id": order_id}


@router.get("/ml-stats")
async def ml_stats(db: AsyncSession = Depends(get_db)):
    """
    ML model diagnostikasi:
    - Interaction ma'lumotlar soni
    - SVD explained variance (model 'aniqligi')
    """
    import numpy as np
    from sklearn.decomposition import TruncatedSVD

    result = await db.execute(select(models.ProductInteraction))
    interactions = result.scalars().all()
    total           = len(interactions)
    unique_users    = len({str(i.user_id)    for i in interactions})
    unique_products = len({str(i.product_id) for i in interactions})

    svd_variance   = None
    svd_components = None
    if total >= 5 and unique_users >= 2 and unique_products >= 2:
        _W       = {"purchase": 3, "click": 2, "view": 1}
        user_ids = list({str(i.user_id)    for i in interactions})
        prod_ids = list({str(i.product_id) for i in interactions})
        u_enc    = {uid: idx for idx, uid in enumerate(user_ids)}
        p_enc    = {pid: idx for idx, pid in enumerate(prod_ids)}

        matrix = np.zeros((len(user_ids), len(prod_ids)), dtype=np.float32)
        for inter in interactions:
            ui = u_enc.get(str(inter.user_id))
            pi = p_enc.get(str(inter.product_id))
            if ui is not None and pi is not None:
                matrix[ui, pi] = max(matrix[ui, pi], _W.get(inter.interaction_type.value, 1))

        n   = min(10, unique_users - 1, unique_products - 1)
        svd = TruncatedSVD(n_components=n, random_state=42)
        svd.fit_transform(matrix)
        svd_variance   = round(float(svd.explained_variance_ratio_.sum()), 4)
        svd_components = n

    return {
        "postgres_interactions": {
            "total":           total,
            "unique_users":    unique_users,
            "unique_products": unique_products,
        },
        "svd_model": {
            "status":             "trained" if svd_variance is not None else "insufficient_data",
            "explained_variance": svd_variance,
            "n_components":       svd_components,
            "note": (
                "0.7+ = yaxshi, 0.5-0.7 = qoniqarli, <0.5 = ko'proq ma'lumot kerak"
                if svd_variance is not None else
                f"Kamida 5 ta interaksiya kerak (hozir: {total})"
            ),
        },
        "recommendation_pipeline": [
            "1. SVD Matrix Factorization (sklearn) — asosiy",
            "2. SQL collaborative filtering (product_interactions self-join) — fallback",
            "3. PostgreSQL top-by-views                                     — final fallback",
        ],
    }
