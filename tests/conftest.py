"""Shared pytest fixtures for the Engram test suite."""

import asyncio

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from engram.models import Base

_IN_MEMORY_SQLITE = "sqlite+aiosqlite:///:memory:?cache=shared"


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create the event loop for the async test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Fresh, function-scoped engine using a single persistent in-memory connection."""
    eng = create_async_engine(
        _IN_MEMORY_SQLITE,
        echo=False,
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """Yield a fresh AsyncSession backed by the current function-scoped engine."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess
