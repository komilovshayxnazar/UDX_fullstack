"""
rate_limiter.py — Centralised rate limit definitions using slowapi.

Usage in a router:
    from core.rate_limiter import limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    @router.post("/endpoint")
    @limiter.limit("5/minute")
    async def my_endpoint(request: Request, ...):
        ...

Limits are keyed by IP address by default.
For authenticated endpoints, swap get_remote_address with a user-id extractor.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
