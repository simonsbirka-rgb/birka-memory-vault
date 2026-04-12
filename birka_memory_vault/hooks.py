from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional

from . import models, schemas

class MemoryRetrievalHooks:
    """
    MVP hooks for retrieving memory context at different stages of the agent lifecycle.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def session_start_hook(self, limit: int = 10) -> schemas.SessionStartContext:
        """
        Invoked when a Birka session starts.
        Retrieves foundational memory context (e.g., recent memories).
        """
        query = select(models.MemoryEntry).order_by(desc(models.MemoryEntry.created_at)).limit(limit)
        result = await self.session.execute(query)
        recent_memories = result.scalars().all()

        return schemas.SessionStartContext(
            recent_memories=[schemas.MemoryEntryResponse.model_validate(m) for m in recent_memories]
        )

    async def per_message_hook(self, tags: Optional[List[str]] = None, limit: int = 5) -> schemas.MessageContext:
        """
        Invoked for each message to retrieve relevant context.
        For MVP, it fetches recent memories and filters by overlapping tags.
        """
        tags = tags or []

        # Since JSON array filtering varies across dialects (SQLite vs Postgres),
        # we fetch a larger recent batch and filter in Python for MVP.
        query = select(models.MemoryEntry).order_by(desc(models.MemoryEntry.created_at)).limit(50)
        result = await self.session.execute(query)
        memories = result.scalars().all()

        relevant_memories = []
        if tags:
            for m in memories:
                if any(t in m.tags for t in tags):
                    relevant_memories.append(m)

        # If no tags provided or none matched, fallback to the most recent ones
        if not relevant_memories:
            relevant_memories = memories[:limit]

        return schemas.MessageContext(
            relevant_memories=[schemas.MemoryEntryResponse.model_validate(m) for m in relevant_memories[:limit]]
        )
