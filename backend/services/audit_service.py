"""
audit_service.py — Convenience wrapper for writing audit logs from any router.
"""

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

import models


async def log(
    db: AsyncSession,
    user: models.User,
    action: models.AuditAction,
    detail: dict,
    request: Request,
    success: bool = True,
):
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    entry = models.AuditLog(
        actor_id=user.id,
        action=action,
        detail=detail,
        ip_address=ip,
        success=success,
    )
    db.add(entry)
    await db.commit()
