import datetime
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

import asyncio

from birka_memory_vault.database import engine, Base
from birka_memory_vault.models import MemoryEntry
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

async def test_insert():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Added references=[] to satisfy NOT NULL constraint
        entry = MemoryEntry(
            type="decision",
            title="Switching to Gemini for ACP",
            content="Switched from failing Qwen subagents to Gemini ACP runtime.",
            tags=["birka", "infrastructure", "acp"],
            references=[],
            source_file="memory/2026-03-29.md",
            created_at=datetime.datetime.now(datetime.timezone.utc)
        )
        session.add(entry)
        await session.commit()
        print(f"Successfully inserted MemoryEntry with ID: {entry.id}")

if __name__ == "__main__":
    asyncio.run(test_insert())
