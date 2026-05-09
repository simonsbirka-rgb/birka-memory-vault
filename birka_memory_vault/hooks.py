# birka_memory_vault/hooks.py
from typing import List
from .database import AsyncSessionLocal
from .events import MemoryEventManager
from .schemas import MemoryEntryCreate


async def session_start_hook(limit: int = 10) -> dict:
    """Load recent memories to prime agent context."""
    async with AsyncSessionLocal() as session:
        manager = MemoryEventManager(session)
        recent = await manager.semantic_search(
            query="recent activity and decisions",
            n_results=limit,
        )
        return {"recent_memories": recent}


async def pre_compression_save(entries: List[dict]) -> int:
    """Save entries before context compression destroys them."""
    async with AsyncSessionLocal() as session:
        manager = MemoryEventManager(session)
        saved = 0
        for e in entries:
            entry = MemoryEntryCreate(
                type=e.get("type", "session_turn"),
                title=e.get("title", "auto-saved turn"),
                content=e.get("content", ""),
                tags=e.get("tags", []),
                references=e.get("references", []),
                source_file=e.get("source_file", "auto_save"),
                agent_id=e.get("agent_id"),
            )
            await manager.add_memory_entry(entry)
            saved += 1
        return saved
