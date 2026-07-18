"""
memdb_store.py — client wrapper for the Go memdb server (in-memory KV +
WAL, see /In-Memory database with WAL). Durable primary store for OTP /
session / short-lived token data — survives a container restart via the
server's WAL replay, unlike the in-process dict fallback in routers/auth.py.

MEMDB_HOST sozlanmagan yoki server mavjud bo'lmasa barcha operatsiyalar
jim o'tkazib yuboriladi (no-op fallback) — server ishdan chiqmaydi.

memdb has no native TTL (unlike Redis SETEX), so callers encode the
expiry inside the JSON value and check it on read — the same pattern
routers/auth.py already uses for its in-process dict fallback.

The vendored client (memdb/client.py) is a blocking socket client, so
every call here is dispatched through asyncio.to_thread to avoid
stalling the event loop.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from memdb import MemDB, MemDBError, PooledMemDB  # noqa: F401 — MemDB/MemDBError re-exported for callers

logger = logging.getLogger(__name__)

_pool: Optional[PooledMemDB] = None


async def init_memdb() -> None:
    global _pool
    host = os.getenv("MEMDB_HOST")
    if not host:
        logger.info("[MEMDB] MEMDB_HOST topilmadi — memdb o'chirilgan (no-op)")
        return
    port = int(os.getenv("MEMDB_PORT", "5455"))
    pool = PooledMemDB(host=host, port=port, size=16)
    try:
        def _ping() -> None:
            with pool.connection() as conn:
                conn.ping()
        await asyncio.to_thread(_ping)
        _pool = pool
        logger.info("[MEMDB] memdb ulandi: %s:%s", host, port)
    except Exception as exc:
        logger.warning("[MEMDB] memdb ulanmadi (%s) — o'chirilgan", exc)
        pool.close()
        _pool = None


async def close_memdb() -> None:
    global _pool
    if _pool is not None:
        await asyncio.to_thread(_pool.close)
        _pool = None


def is_memdb_enabled() -> bool:
    return _pool is not None


async def memdb_ping() -> bool:
    """Used by /health — cheap liveness probe."""
    pool = _pool
    if pool is None:
        return False
    try:
        def _do() -> None:
            with pool.connection() as conn:
                conn.ping()
        await asyncio.to_thread(_do)
        return True
    except Exception as exc:
        logger.warning("[MEMDB] ping error: %s", exc)
        return False


async def memdb_set(key: str, value: bytes) -> bool:
    """True agar yozildi. False — memdb yo'q yoki xato (caller keyingi tierga tushadi)."""
    pool = _pool
    if pool is None:
        return False
    try:
        def _do() -> None:
            with pool.connection() as conn:
                conn.set(key, value)
        await asyncio.to_thread(_do)
        return True
    except Exception as exc:
        logger.warning("[MEMDB] set error key=%s: %s", key, exc)
        return False


async def memdb_get(key: str) -> Optional[bytes]:
    pool = _pool
    if pool is None:
        return None
    try:
        def _do() -> Optional[bytes]:
            with pool.connection() as conn:
                return conn.get(key)
        return await asyncio.to_thread(_do)
    except Exception as exc:
        logger.warning("[MEMDB] get error key=%s: %s", key, exc)
        return None


async def memdb_delete(key: str) -> bool:
    pool = _pool
    if pool is None:
        return False
    try:
        def _do() -> bool:
            with pool.connection() as conn:
                return conn.delete(key)
        return await asyncio.to_thread(_do)
    except Exception as exc:
        logger.warning("[MEMDB] delete error key=%s: %s", key, exc)
        return False
