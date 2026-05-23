"""Async engine and session lifecycle."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def configure_engine(database_url: str) -> None:
    """Create singleton async engine/session factory."""

    global _engine, _session_factory
    if _engine is not None:
        return
    _engine = create_async_engine(database_url, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        msg = "Database not configured"
        raise RuntimeError(msg)
    async with _session_factory() as session:
        yield session


async def dispose_db() -> None:
    """Close pooled connections (lifespan shutdown / isolated tests)."""

    global _engine, _session_factory
    eng = _engine
    _engine = None
    _session_factory = None
    if eng is not None:
        await eng.dispose()
