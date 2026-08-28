"""SQLAlchemy 2 async database engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from agent_gateway.config.settings import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """Return or create the async database engine."""
    global _engine
    if _engine is None:
        cfg = settings or get_settings()
        _engine = create_async_engine(
            cfg.database_url,
            echo=cfg.app_debug,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    """Return or create the async session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine(settings)
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db(settings: Settings | None = None) -> None:
    """Create all tables if they do not exist."""
    import agent_gateway.storage.models  # noqa: F401 — register ORM metadata

    engine = get_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_connection(settings: Settings | None = None) -> bool:
    """Verify database connectivity for readiness probes."""
    from sqlalchemy import text

    try:
        engine = get_engine(settings)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def close_db() -> None:
    """Dispose of the database engine."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
