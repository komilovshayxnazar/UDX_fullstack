"""
audit_service.py — Convenience wrapper for writing audit logs from any router.
"""

from fastapi import Request
import models


async def log(
    user: models.User,
    action: models.AuditAction,
    detail: dict,
    request: Request,
    success: bool = True,
):
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    entry = models.AuditLog(
        user_id=str(user.id),
        action=action,
        detail=detail,
        ip_address=ip,
        success=success,
    )
    await entry.insert()
