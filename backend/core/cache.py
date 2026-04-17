"""
Redis cache — ixtiyoriy.

REDIS_URL sozlanmagan yoki Redis mavjud bo'lmasa barcha operatsiyalar
jim o'tkazib yuboriladi (no-op fallback) — server ishdan chiqmaydi.

TTL konstantalari:
  CATEGORIES_TTL  = 3600 s  (1 soat)  — deyarli o'zgarmaydigan ma'lumot
  RECS_TTL        = 3600 s  (1 soat)  — SVD hisobi og'ir
  PRODUCTS_TTL    =  300 s  (5 daqiqa) — tez-tez o'zgaradigan narxlar
  PROFILE_TTL     = 1800 s  (30 daqiqa) — seller profili
  REVIEWS_TTL     =  900 s  (15 daqiqa) — sharhlar

Kalitlar:
  categories
  products:{skip}:{limit}:{is_b2b}:{category_id}:{q}
  recs:{user_id}:{limit}
  public_profile:{user_id}
  seller_reviews:{seller_id}:{skip}:{limit}
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

CATEGORIES_TTL = 3600
RECS_TTL       = 3600
PRODUCTS_TTL   = 300
PROFILE_TTL    = 1800
REVIEWS_TTL    = 900

_redis = None


async def init_cache() -> None:
    global _redis
    url = os.getenv("REDIS_URL")
    if not url:
        logger.info("[CACHE] REDIS_URL topilmadi — cache o'chirilgan (no-op)")
        return
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
        await client.ping()
        _redis = client
        logger.info("[CACHE] Redis ulandi: %s", url)
    except Exception as exc:
        logger.warning("[CACHE] Redis ulanmadi (%s) — cache o'chirilgan", exc)
        _redis = None


async def close_cache() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


# ── asosiy operatsiyalar ──────────────────────────────────────────────────────

async def cache_get(key: str) -> Any | None:
    if _redis is None:
        return None
    try:
        raw = await _redis.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:
        logger.warning("[CACHE] get error key=%s: %s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    if _redis is None:
        return
    try:
        await _redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.warning("[CACHE] set error key=%s: %s", key, exc)


async def cache_delete(key: str) -> None:
    if _redis is None:
        return
    try:
        await _redis.delete(key)
    except Exception as exc:
        logger.warning("[CACHE] delete error key=%s: %s", key, exc)


async def cache_delete_pattern(pattern: str) -> None:
    """SCAN + DELETE — large keyspace'da xavfsiz (KEYS ishlatmaydi)."""
    if _redis is None:
        return
    try:
        keys: list[str] = []
        async for key in _redis.scan_iter(pattern):
            keys.append(key)
        if keys:
            await _redis.delete(*keys)
    except Exception as exc:
        logger.warning("[CACHE] delete_pattern error pattern=%s: %s", pattern, exc)
