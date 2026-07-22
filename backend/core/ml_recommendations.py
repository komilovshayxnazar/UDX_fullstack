"""
Recommendation engine — ikki qavatli:

  1. SVD Matrix Factorization (sklearn) — asosiy ML model
     Foydalanuvchi-mahsulot interaksiya matritsasini TruncatedSVD bilan
     faktorizatsiya qiladi va har bir foydalanuvchi uchun bashoratiy ball
     hisoblaydi.  Og'irliklar: purchase=3, click=2, view=1.

  2. SQL collaborative filtering — "Siz ko'rgan mahsulotlarni ko'rgan
     boshqa foydalanuvchilar yana nimalar ko'rgan?" — item-based CF,
     product_interactions jadvali ustidan self-join orqali (Neo4j o'rniga).

  3. Fallback — agar ma'lumot yetarli bo'lmasa
     Bo'sh ro'yxat qaytaradi → `products.py` da `top by views` ishga tushadi.
"""

from __future__ import annotations

import logging
import uuid
from typing import List

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import models
from core.cache import cache_get, cache_set, RECS_TTL

logger = logging.getLogger(__name__)

# Interaction type weights for the interaction matrix
_WEIGHTS = {"purchase": 3, "click": 2, "view": 1}


async def recommend_for_user(db: AsyncSession, user_id: str, limit: int = 10) -> List[str]:
    """
    Async wrapper: tries SVD first, then SQL CF, returns product id list.
    Empty list means "no personalised recs" — caller should use its own fallback.
    Results are cached in Redis for RECS_TTL seconds (default 1 hour).
    """
    cache_key = f"recs:{user_id}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        logger.info("[ML] Cache hit for user %s", user_id)
        return cached

    # ── 1. SVD ──────────────────────────────────────────────────────────────
    try:
        ids = await _svd_recommend(db, user_id, limit)
        if ids:
            logger.info("[ML] SVD returned %d recs for user %s", len(ids), user_id)
            await cache_set(cache_key, ids, ttl=RECS_TTL)
            return ids
    except Exception as e:
        logger.warning("[ML] SVD failed: %s", e)

    # ── 2. SQL collaborative filtering ───────────────────────────────────────
    try:
        ids = await _sql_cf(db, user_id, limit)
        if ids:
            logger.info("[ML] SQL CF returned %d recs for user %s", len(ids), user_id)
            await cache_set(cache_key, ids, ttl=RECS_TTL)
            return ids
    except Exception as e:
        logger.warning("[ML] SQL CF failed: %s", e)

    return []


# ── SVD implementation ────────────────────────────────────────────────────

async def _svd_recommend(db: AsyncSession, user_id: str, limit: int) -> List[str]:
    result = await db.execute(select(models.ProductInteraction))
    interactions = result.scalars().all()

    if len(interactions) < 5:
        return []

    user_ids = list({str(i.user_id) for i in interactions})
    product_ids = list({str(i.product_id) for i in interactions})

    if len(user_ids) < 2 or len(product_ids) < 2:
        return []

    if user_id not in user_ids:
        return []  # cold start

    user_enc = {uid: idx for idx, uid in enumerate(user_ids)}
    prod_enc = {pid: idx for idx, pid in enumerate(product_ids)}
    prod_dec = {idx: pid for pid, idx in prod_enc.items()}

    # Build weighted interaction matrix
    matrix = np.zeros((len(user_ids), len(product_ids)), dtype=np.float32)
    for inter in interactions:
        ui = user_enc.get(str(inter.user_id))
        pi = prod_enc.get(str(inter.product_id))
        if ui is not None and pi is not None:
            w = _WEIGHTS.get(inter.interaction_type.value, 1)
            matrix[ui, pi] = max(matrix[ui, pi], w)

    # TruncatedSVD — n_components capped by matrix dimensions
    n_components = min(10, len(user_ids) - 1, len(product_ids) - 1)
    if n_components < 1:
        return []

    svd = TruncatedSVD(n_components=n_components, random_state=42)
    user_factors = svd.fit_transform(matrix)        # shape: (users, k)
    item_factors = svd.components_.T                # shape: (items, k)

    # Predicted scores for this user
    u_idx = user_enc[user_id]
    scores = user_factors[u_idx] @ item_factors.T

    # Mask products the user already interacted with
    seen = {prod_enc[str(i.product_id)]
            for i in interactions
            if str(i.user_id) == user_id and str(i.product_id) in prod_enc}

    recs: List[str] = []
    for idx in np.argsort(scores)[::-1]:
        if idx not in seen:
            recs.append(prod_dec[int(idx)])
        if len(recs) >= limit:
            break

    return recs


# ── SQL collaborative filtering (replaces the old Neo4j Cypher query) ───────

async def _sql_cf(db: AsyncSession, user_id: str, limit: int) -> List[str]:
    """
    "People who interacted with what you interacted with also interacted
    with..." — a self-join over product_interactions.
    """
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return []

    U = models.ProductInteraction.__table__.alias("u")
    OTHER = models.ProductInteraction.__table__.alias("other")
    REC = models.ProductInteraction.__table__.alias("rec")

    seen_subq = (
        select(models.ProductInteraction.product_id)
        .where(models.ProductInteraction.user_id == uid)
    )

    stmt = (
        select(REC.c.product_id, func.count().label("score"))
        .select_from(U)
        .join(OTHER, (OTHER.c.product_id == U.c.product_id) & (OTHER.c.user_id != U.c.user_id))
        .join(REC, REC.c.user_id == OTHER.c.user_id)
        .where(U.c.user_id == uid)
        .where(REC.c.product_id.not_in(seen_subq))
        .group_by(REC.c.product_id)
        .order_by(func.count().desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    ids = [str(row[0]) for row in result.all()]

    if len(ids) < limit:
        popular = await _sql_popular(db, limit)
        seen_result = await db.execute(seen_subq)
        seen_ids = {str(pid) for (pid,) in seen_result.all()}
        for pid in popular:
            if pid not in ids and pid not in seen_ids:
                ids.append(pid)
            if len(ids) >= limit:
                break

    return ids


async def _sql_popular(db: AsyncSession, limit: int) -> List[str]:
    stmt = (
        select(models.ProductInteraction.product_id, func.count().label("cnt"))
        .group_by(models.ProductInteraction.product_id)
        .order_by(func.count().desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [str(row[0]) for row in result.all()]
