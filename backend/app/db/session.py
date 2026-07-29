"""Database session factory and dependency injection."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: Settings) -> AsyncEngine:
    """Create or return the cached async database engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            echo=settings.database_echo,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    """Create or return the cached session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine(settings)
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db(settings: Settings) -> None:
    """Initialize database connection pool (call at startup)."""
    get_engine(settings)
