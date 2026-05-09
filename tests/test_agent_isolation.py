import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from birka_memory_vault.models import Base
from birka_memory_vault.events import MemoryEventManager
from birka_memory_vault.schemas import MemoryEntryCreate
from birka_memory_vault.vector_store import VectorStore
import os
import shutil

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="function")
async def session():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()

@pytest.fixture
def vector_store():
    test_dir = "/tmp/test_chroma_agent"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    vs = VectorStore(test_dir)
    yield vs
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

@pytest.mark.asyncio
async def test_agent_isolation(session, vector_store):
    manager = MemoryEventManager(session, vector_store=vector_store)

    await manager.add_memory_entry(MemoryEntryCreate(
        type="private", title="Agent A Secret", content="I am A",
        tags=[], source_file="a.md", agent_id="agent_a"
    ))
    await manager.add_memory_entry(MemoryEntryCreate(
        type="private", title="Agent B Secret", content="I am B",
        tags=[], source_file="b.md", agent_id="agent_b"
    ))

    a_memories = await manager.get_agent_memories("agent_a")
    assert len(a_memories) == 1
    assert a_memories[0].title == "Agent A Secret"

    b_memories = await manager.get_agent_memories("agent_b")
    assert len(b_memories) == 1
    assert b_memories[0].title == "Agent B Secret"
