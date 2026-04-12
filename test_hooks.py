import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

import asyncio

from birka_memory_vault.database import engine, Base
from birka_memory_vault.models import MemoryEntry
from birka_memory_vault.hooks import MemoryRetrievalHooks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

async def test_hooks():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create some test data
        entries = [
            MemoryEntry(
                type="decision",
                title="Use asyncio",
                content="Asyncio is great.",
                tags=["python", "async"],
                references=[],
                source_file="memory/1.md",
                created_at=datetime.datetime.now(datetime.timezone.utc)
            ),
            MemoryEntry(
                type="observation",
                title="Postgres issue",
                content="Connection pool full.",
                tags=["db", "postgres"],
                references=[],
                source_file="memory/2.md",
                created_at=datetime.datetime.now(datetime.timezone.utc)
            )
        ]
        session.add_all(entries)
        await session.commit()

        hooks = MemoryRetrievalHooks(session)

        # Test session start
        start_context = await hooks.session_start_hook(limit=2)
        assert len(start_context.recent_memories) >= 2
        print(f"session_start_hook returned {len(start_context.recent_memories)} memories")

        # Test per message matching tags
        msg_context = await hooks.per_message_hook(tags=["python"], limit=2)
        assert len(msg_context.relevant_memories) > 0
        assert any(m.title == "Use asyncio" for m in msg_context.relevant_memories)
        print(f"per_message_hook (with tags) returned {len(msg_context.relevant_memories)} memories")

        # Test per message no tags (fallback to recent)
        msg_context_no_tags = await hooks.per_message_hook(limit=1)
        assert len(msg_context_no_tags.relevant_memories) == 1
        print(f"per_message_hook (no tags) returned {len(msg_context_no_tags.relevant_memories)} memories")

if __name__ == "__main__":
    asyncio.run(test_hooks())
