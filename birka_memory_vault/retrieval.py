# birka_memory_vault/retrieval.py
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta
from . import models, schemas, events


class HybridRetriever:
    """MemPalace-inspired hybrid: semantic + keyword + temporal proximity."""

    def __init__(self, session: AsyncSession, manager: events.MemoryEventManager):
        self.session = session
        self.manager = manager

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        recency_weight: float = 0.3,
        semantic_weight: float = 0.5,
        keyword_weight: float = 0.2,
    ) -> List[schemas.MemoryEntryResponse]:
        # 1. Semantic candidates (top 20) — pure vector similarity
        semantic_hits = await self.manager.semantic_search(query, n_results=20)

        # 2. Keyword candidates — SQL LIKE match (handles tags naturally)
        kw_result = await self.session.execute(
            select(models.MemoryEntry)
            .where(
                (models.MemoryEntry.title.ilike(f"%{query}%")) |
                (models.MemoryEntry.content.ilike(f"%{query}%"))
            )
            .order_by(desc(models.MemoryEntry.created_at))
            .limit(20)
        )
        keyword_entries = {e.id: e for e in kw_result.scalars().all()}

        # 3. Score and merge
        scored = {}
        for entry in semantic_hits:
            scored[entry.id] = scored.get(entry.id, 0) + semantic_weight
        for eid in keyword_entries:
            scored[eid] = scored.get(eid, 0) + keyword_weight

        # 4. Temporal boost — recent entries get bonus
        now = datetime.utcnow()
        cutoff = now - timedelta(days=7)
        all_ids = set(scored.keys())
        if all_ids:
            result = await self.session.execute(
                select(models.MemoryEntry).where(models.MemoryEntry.id.in_(all_ids))
            )
            for e in result.scalars().all():
                if e.created_at and e.created_at > cutoff:
                    age_days = (now - e.created_at).days
                    boost = recency_weight * (1.0 - age_days / 7.0)
                    scored[e.id] = scored.get(e.id, 0) + max(0, boost)

        # 5. Sort by score, return top N
        sorted_ids = sorted(scored, key=scored.get, reverse=True)[:limit]
        result = await self.session.execute(
            select(models.MemoryEntry).where(models.MemoryEntry.id.in_(sorted_ids))
        )
        entries = {e.id: e for e in result.scalars().all()}
        return [schemas.MemoryEntryResponse.model_validate(entries[eid])
                for eid in sorted_ids if eid in entries]
