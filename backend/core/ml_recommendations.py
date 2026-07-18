"""
Recommendation engine — uch qavatli:

  1. SVD Matrix Factorization (sklearn) — asosiy ML model
     Foydalanuvchi-mahsulot interaksiya matritsasini TruncatedSVD bilan
     faktorizatsiya qiladi va har bir foydalanuvchi uchun bashoratiy ball
     hisoblaydi.  Og'irliklar: purchase=3, click=2, view=1.

  2. Neo4j Collaborative Filtering — agar Neo4j ishlasa
     "Siz ko'rgan mahsulotlarni ko'rgan boshqa foydalanuvchilar yana nimalar
     ko'rgan?" — klassik item-based CF grafdagi INTERACTED munosabatlari orqali.

  3. Fallback — agar ma'lumot yetarli bo'lmasa
     Bo'sh ro'yxat qaytaradi → `products.py` da `top by views` ishga tushadi.
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np
from sklearn.decomposition import TruncatedSVD

import models
from core import neo4j_db
from core.cache import cache_get, cache_set, RECS_TTL

logger = logging.getLogger(__name__)

# Interaction type weights for the interaction matrix
_WEIGHTS = {"purchase": 3, "click": 2, "view": 1}


async def recommend_for_user(user_id: str, limit: int = 10) -> List[str]:
    """
    Async wrapper: tries SVD first, then Neo4j CF, returns product id list.
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
        ids = await _svd_recommend(user_id, limit)
        if ids:
            logger.info("[ML] SVD returned %d recs for user %s", len(ids), user_id)
            await cache_set(cache_key, ids, ttl=RECS_TTL)
            return ids
    except Exception as e:
        logger.warning("[ML] SVD failed: %s", e)

    # ── 2. Neo4j CF ─────────────────────────────────────────────────────────
    if neo4j_db.is_available():
        try:
            ids = _neo4j_cf(user_id, limit)
            if ids:
                logger.info("[ML] Neo4j CF returned %d recs for user %s", len(ids), user_id)
                await cache_set(cache_key, ids, ttl=RECS_TTL)
                return ids
        except Exception as e:
            logger.warning("[ML] Neo4j CF failed: %s", e)

    return []


# ── SVD implementation ────────────────────────────────────────────────────────

async def _svd_recommend(user_id: str, limit: int) -> List[str]:
    interactions = await models.ProductInteraction.find_all().to_list()

    if len(interactions) < 5:
        return []

    user_ids    = list({i.user_id    for i in interactions})
    product_ids = list({i.product_id for i in interactions})

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
        ui = user_enc.get(inter.user_id)
        pi = prod_enc.get(inter.product_id)
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
    u_idx     = user_enc[user_id]
    scores    = user_factors[u_idx] @ item_factors.T

    # Mask products the user already interacted with
    seen = {prod_enc[i.product_id]
            for i in interactions
            if i.user_id == user_id and i.product_id in prod_enc}

    recs: List[str] = []
    for idx in np.argsort(scores)[::-1]:
        if idx not in seen:
            recs.append(prod_dec[int(idx)])
        if len(recs) >= limit:
            break

    return recs


def _svd_explained_variance() -> float | None:
    """
    Model 'aniqligi' ko'rsatkichi sifatida SVD explained variance ratio ni
    hisoblaydi.  Bu 0–1 oralig'ida qiymat qaytaradi; 1.0 = perfect fit.
    Amalda 0.5–0.8 orasida bo'lishi normal.
    """
    import asyncio
    import sys

    # Faqat debug/test maqsadida sinxron ishlatish uchun
    if sys.platform == "win32":
        loop = asyncio.new_event_loop()
    else:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()

    try:
        interactions = loop.run_until_complete(
            models.ProductInteraction.find_all().to_list()
        )
    except Exception:
        return None

    if len(interactions) < 5:
        return None

    user_ids    = list({i.user_id    for i in interactions})
    product_ids = list({i.product_id for i in interactions})
    user_enc    = {uid: idx for idx, uid in enumerate(user_ids)}
    prod_enc    = {pid: idx for idx, pid in enumerate(product_ids)}

    matrix = np.zeros((len(user_ids), len(product_ids)), dtype=np.float32)
    for inter in interactions:
        ui = user_enc.get(inter.user_id)
        pi = prod_enc.get(inter.product_id)
        if ui is not None and pi is not None:
            w = _WEIGHTS.get(inter.interaction_type.value, 1)
            matrix[ui, pi] = max(matrix[ui, pi], w)

    n_components = min(10, len(user_ids) - 1, len(product_ids) - 1)
    if n_components < 1:
        return None

    svd = TruncatedSVD(n_components=n_components, random_state=42)
    svd.fit_transform(matrix)
    return float(svd.explained_variance_ratio_.sum())


# ── Neo4j CF implementation ───────────────────────────────────────────────────

def _neo4j_cf(user_id: str, limit: int) -> List[str]:
    # Check history
    has_history = neo4j_db.execute_query(
        "MATCH (u:User {id: $uid})-[:INTERACTED]->() RETURN count(u) > 0 AS h",
        {"uid": user_id},
    )
    if not (has_history and has_history[0]["h"]):
        return _neo4j_popular(limit)

    rows = neo4j_db.execute_query(
        """
        MATCH (u:User {id: $uid})-[:INTERACTED]->(p:Product)
              <-[:INTERACTED]-(other:User)-[:INTERACTED]->(rec:Product)
        WHERE NOT (u)-[:INTERACTED]->(rec)
        RETURN rec.id AS id, count(*) AS score
        ORDER BY score DESC
        LIMIT $lim
        """,
        {"uid": user_id, "lim": limit},
    )
    ids = [r["id"] for r in rows]

    if len(ids) < limit:
        # Foydalanuvchi allaqachon ko'rgan mahsulotlarni popular listdan chiqaramiz
        seen_by_user = {
            r["id"]
            for r in neo4j_db.execute_query(
                "MATCH (:User {id: $uid})-[:INTERACTED]->(p:Product) RETURN p.id AS id",
                {"uid": user_id},
            )
        }
        popular = _neo4j_popular(limit)
        for pid in popular:
            if pid not in ids and pid not in seen_by_user:
                ids.append(pid)
            if len(ids) >= limit:
                break
    return ids


def _neo4j_popular(limit: int) -> List[str]:
    rows = neo4j_db.execute_query(
        """
        MATCH ()-[r:INTERACTED]->(p:Product)
        RETURN p.id AS id, count(r) AS cnt
        ORDER BY cnt DESC
        LIMIT $lim
        """,
        {"lim": limit},
    )
    return [r["id"] for r in rows]
