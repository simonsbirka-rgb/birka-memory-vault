import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .models import Base

# Determine database URL based on environment variables
# SQLite (dev) + PostgreSQL (prod)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./birka_memory.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
