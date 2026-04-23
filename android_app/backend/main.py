from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import os
import logging

logging.basicConfig(level=logging.INFO)

# Load environment variables first
load_dotenv()

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
import database

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("[INIT] Connecting to database...")
    try:
        await database.init_db()
        logging.info("[INIT] Database initialized")
    except Exception as e:
        logging.critical(f"[INIT] Database connection failed: {e}")
        raise RuntimeError(f"Cannot start without database: {e}")
    await init_cache()
    await start_bot()
    yield
    logging.info("[INIT] Shutting down...")
    await stop_bot()
    await close_cache()


app = FastAPI(title="UDX API", lifespan=lifespan)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Static files — faqat R2 sozlanmagan bo'lsa (lokal fallback)
if not os.getenv("R2_ACCOUNT_ID"):
    os.makedirs("uploads", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS
_raw_origins = os.getenv("ALLOWED_ORIGINS", "https://udx-marketplace.store,https://localhost:5173,https://10.0.2.2:8000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Idempotency-Key"],
)

# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health_check():
    """Servis holati: MongoDB, Redis, Storage."""
    from core.cache import get_redis
    from core.storage import _r2_configured

    result: dict = {"status": "ok", "services": {}}

    # MongoDB
    try:
        await database.motor_client.admin.command("ping")
        result["services"]["mongodb"] = "ok"
    except Exception as exc:
        result["services"]["mongodb"] = f"error: {exc}"
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

# Dev router — FAQAT development muhitida (production'da hech qachon!)
_ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
if _ENVIRONMENT != "production":
    app.include_router(dev.router)
    logging.warning(
        "[SECURITY] Dev router YOQILGAN (ENVIRONMENT=%s). "
        "Production'da ENVIRONMENT=production qo'ying!", _ENVIRONMENT
    )
