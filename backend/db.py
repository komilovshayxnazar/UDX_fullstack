"""
db.py — Async SQLAlchemy 2.0 engine/session setup for PostgreSQL.

Replaces the old Mongo/Beanie `database.py`. Alembic (not the app) owns
schema creation/migration, so there is no `init_db()` startup call —
only an async engine + sessionmaker + a `get_db()` FastAPI dependency.
"""
import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://udx:udx@localhost:5432/udx",
)

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models (see models.py)."""
    pass


async def get_db():
    """FastAPI dependency yielding an AsyncSession, committed/rolled back per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Call on app shutdown to close the connection pool cleanly."""
    await engine.dispose()
