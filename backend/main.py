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

import models
import database

# Import all routers
from routers import auth, users, products, orders, chat, weather, dev, contracts, payments

# Import services (registers event handlers as a side effect)
from services import event_bus as _eb   # noqa: F401 — side-effect import
import services.event_handlers          # noqa: F401 — registers @event_bus.on handlers

# Rate limiter
from core.rate_limiter import limiter

# Lifespan
from contextlib import asynccontextmanager
from telegram_bot import start_bot, stop_bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[INIT] Connecting to database...")
    try:
        await database.init_db()
        print("[INIT] Database initialized")
    except Exception as e:
        print(f"[INIT] Error initializing database: {e}")
    await start_bot()
    yield
    print("[INIT] Disconnecting from database...")
    await stop_bot()


app = FastAPI(title="UDX API", lifespan=lifespan)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Static files
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(chat.router)
app.include_router(weather.router)
app.include_router(dev.router)
app.include_router(contracts.router)
app.include_router(payments.router)
