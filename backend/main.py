from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import os
import uuid
import logging

logging.basicConfig(level=logging.INFO)

from core.jsonlog import init_json_logging, trace_id_var
init_json_logging()

# Load environment variables first
load_dotenv()

# Fail-closed environment gate. Defaults to "production" so a forgotten
# ENVIRONMENT env var does not silently enable dev routes or accept
# ephemeral crypto keys.
_ENVIRONMENT = os.getenv("ENVIRONMENT", "production").lower()
_IS_PROD = _ENVIRONMENT == "production"


def _require_prod_env(name: str) -> str:
    """Return env value or raise on missing when running in production."""
    val = os.getenv(name, "").strip()
    if not val and _IS_PROD:
        raise RuntimeError(
            f"[CONFIG] {name} must be set when ENVIRONMENT=production"
        )
    return val

# Sentry — SENTRY_DSN sozlanmagan bo'lsa jim o'tadi
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

_sentry_dsn = os.getenv("SENTRY_DSN")
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.1,   # 10% request tracing
        send_default_pii=False,
    )
    logging.info("[INIT] Sentry initialized")

import models
import db as db_module
from sqlalchemy import text

# Import all routers
from routers import auth, users, products, orders, chat, weather, dev, contracts, payments
from routers.click_payment import router as click_router
from routers.reviews import router as reviews_router, fraud_router

# Import services (registers event handlers as a side effect)
from services import event_bus as _eb   # noqa: F401 — side-effect import
import services.event_handlers          # noqa: F401 — registers @event_bus.on handlers

# Rate limiter
from core.rate_limiter import limiter

# Lifespan
from contextlib import asynccontextmanager
from telegram_bot import start_bot, stop_bot
from core.cache import init_cache, close_cache
from core.memdb_store import init_memdb, close_memdb


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is owned by Alembic (`alembic upgrade head`, run before uvicorn
    # starts — see backend/Dockerfile), not by app startup. We just verify
    # connectivity here so a misconfigured DATABASE_URL fails fast.
    logging.info("[INIT] Verifying database connectivity...")
    try:
        async with db_module.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logging.info("[INIT] Database reachable")
    except Exception as e:
        logging.critical(f"[INIT] Database connection failed: {e}")
        raise RuntimeError(f"Cannot start without database: {e}")
    await init_cache()
    await init_memdb()
    await start_bot()
    yield
    logging.info("[INIT] Shutting down...")
    await stop_bot()
    await close_memdb()
    await close_cache()
    await db_module.dispose_engine()


app = FastAPI(title="UDX API", lifespan=lifespan)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Static files — faqat R2 sozlanmagan bo'lsa (lokal fallback)
if not os.getenv("R2_ACCOUNT_ID"):
    os.makedirs("uploads", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS — default to the production origin only. Additional origins
# (dev, staging, mobile emulator loopback) must be listed explicitly
# in ALLOWED_ORIGINS. In production we also refuse to accept any
# origin that looks like localhost so a stray dev value cannot open
# credentialed CSRF against the API.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "https://udx-marketplace.store")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
if _IS_PROD:
    bad = [o for o in ALLOWED_ORIGINS if "localhost" in o or "10.0.2.2" in o or "127.0.0.1" in o]
    if bad:
        raise RuntimeError(
            f"[CONFIG] ALLOWED_ORIGINS contains dev origins in production: {bad}"
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Idempotency-Key"],
)


# ── Trace ID ─────────────────────────────────────────────────────────────────
# Every request gets a trace_id (reused from an upstream X-Trace-Id header if
# present, e.g. set by the gateway/nginx front-end) that tags every JSON-line
# log record emitted while handling it — see core/jsonlog.py + the
# Distributed Log Aggregator's `trace_id=` query filter.

@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex
    token = trace_id_var.set(trace_id)
    try:
        response = await call_next(request)
    finally:
        trace_id_var.reset(token)
    response.headers["X-Trace-Id"] = trace_id
    return response


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health_check():
    """Servis holati: PostgreSQL, Redis, Storage."""
    from core.cache import get_redis
    from core.storage import _r2_configured
    from core.memdb_store import is_memdb_enabled, memdb_ping

    result: dict = {"status": "ok", "services": {}}

    # PostgreSQL
    try:
        async with db_module.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        result["services"]["postgres"] = "ok"
    except Exception as exc:
        result["services"]["postgres"] = f"error: {exc}"
        result["status"] = "degraded"

    # Redis
    r = get_redis()
    if r:
        try:
            await r.ping()
            result["services"]["redis"] = "ok"
        except Exception as exc:
            result["services"]["redis"] = f"error: {exc}"
            result["status"] = "degraded"
    else:
        result["services"]["redis"] = "not configured"

    # memdb (OTP/session store)
    if is_memdb_enabled():
        result["services"]["memdb"] = "ok" if await memdb_ping() else "error: ping failed"
        if result["services"]["memdb"] != "ok":
            result["status"] = "degraded"
    else:
        result["services"]["memdb"] = "not configured"

    # Storage
    result["services"]["storage"] = "r2" if _r2_configured() else "local"

    return result


# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(chat.router)
app.include_router(weather.router)
app.include_router(contracts.router)
app.include_router(payments.router)
app.include_router(reviews_router)
app.include_router(fraud_router)
app.include_router(click_router)

# Dev router — mounted only outside production. `_ENVIRONMENT` is
# resolved above with a fail-closed default of "production".
if not _IS_PROD:
    app.include_router(dev.router)
    logging.warning(
        "[SECURITY] Dev router mounted (ENVIRONMENT=%s). "
        "Set ENVIRONMENT=production to disable.", _ENVIRONMENT
    )
