import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from birka_memory_vault.models import Base
from birka_memory_vault.events import MemoryEventManager
from birka_memory_vault.retrieval import HybridRetriever
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
    test_dir = "/tmp/test_chroma_retrieval"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    vs = VectorStore(test_dir)
    yield vs
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

@pytest.mark.asyncio
async def test_hybrid_retrieval(session, vector_store):
    manager = MemoryEventManager(session, vector_store=vector_store)
    retriever = HybridRetriever(session, manager)

    # Add some memories
    await manager.add_memory_entry(MemoryEntryCreate(
        type="fact", title="Pricing", content="Social Beast costs 500 EUR",
        tags=["pricing"], source_file="test.md"
    ))
    await manager.add_memory_entry(MemoryEntryCreate(
        type="fact", title="Location", content="Office is in Berlin",
        tags=["admin"], source_file="test.md"
    ))

    # Semantic search
    results = await retriever.retrieve("how much does it cost")
    assert len(results) > 0
    assert "Pricing" in results[0].title

    # Keyword search
    results = await retriever.retrieve("Berlin")
    assert len(results) > 0
    assert "Location" in results[0].title
