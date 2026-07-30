"""Asynchronous SQLAlchemy database configuration."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.app.core.config import get_settings


def normalize_async_database_url(database_url: str) -> str:
    """Normalize database URLs for SQLAlchemy's async drivers."""

    if database_url.startswith("postgres://"):
        return database_url.replace(
            "postgres://",
            "postgresql+asyncpg://",
            1,
        )

    if database_url.startswith("postgresql://"):
        return database_url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )

    if database_url.startswith("sqlite://"):
        return database_url.replace(
            "sqlite://",
            "sqlite+aiosqlite://",
            1,
        )

    return database_url


class Base(DeclarativeBase):
    """Base class for all database models."""


settings = get_settings()
DATABASE_URL = normalize_async_database_url(settings.database_url)

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Provide one asynchronous database session per request."""

    async with AsyncSessionLocal() as session:
        yield session