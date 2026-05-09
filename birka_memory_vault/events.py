from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from . import models, schemas

class MemoryEventManager:
    def __init__(self, session: AsyncSession, vector_store=None):
        self.session = session
        from .vector_store import VectorStore
        self.vector_store = vector_store or VectorStore()

    async def add_memory_entry(self, entry: schemas.MemoryEntryCreate) -> models.MemoryEntry:
        db_entry = models.MemoryEntry(
            type=entry.type,
            title=entry.title,
            content=entry.content,
            tags=entry.tags,
            references=entry.references,
            source_file=entry.source_file,
            agent_id=getattr(entry, "agent_id", None)
        )
        self.session.add(db_entry)
        await self.session.commit()
        await self.session.refresh(db_entry)

        self.vector_store.upsert(
            entry_id=db_entry.id,
            content=f"{entry.title}\n{entry.content}",
            metadata={"type": entry.type, "tags": ",".join(entry.tags)}
        )
        return db_entry

    async def get_entries_by_tag(self, tag: str) -> List[models.MemoryEntry]:
        # JSON array filtering in SQLite vs Postgres differs; for simplicity here:
        result = await self.session.execute(select(models.MemoryEntry))
        entries = result.scalars().all()
        return [e for e in entries if tag in e.tags]

    async def compact_entries(self, merged_entry: schemas.MemoryEntryCreate, old_entry_ids: List[int]) -> models.CompactionIndex:
        # 1. Create new merged entry
        new_entry = await self.add_memory_entry(merged_entry)

        # 2. Update old entries to show they were compacted
        result = await self.session.execute(
            select(models.MemoryEntry).where(models.MemoryEntry.id.in_(old_entry_ids))
        )
        old_entries = result.scalars().all()
        for e in old_entries:
            e.compacted_into = new_entry.id

        # 3. Create CompactionIndex record
        compaction = models.CompactionIndex(
            entry_id=new_entry.id,
            merged_ids=old_entry_ids
        )
        self.session.add(compaction)
        await self.session.commit()
        await self.session.refresh(compaction)

        # 4. Sync vector store
        self.vector_store.upsert(
            new_entry.id,
            f"{merged_entry.title}\n{merged_entry.content}",
            {"type": merged_entry.type, "tags": ",".join(merged_entry.tags)}
        )
        self.vector_store.delete(old_entry_ids)

        return compaction

    async def create_snapshot(self, snapshot: schemas.SnapshotIndexCreate) -> models.SnapshotIndex:
        db_snapshot = models.SnapshotIndex(
            entry_ids=snapshot.entry_ids,
            memory_md_hash=snapshot.memory_md_hash
        )
        self.session.add(db_snapshot)
        await self.session.commit()
        await self.session.refresh(db_snapshot)
        return db_snapshot

    async def semantic_search(
        self,
        query: str,
        n_results: int = 10,
    ) -> List[schemas.MemoryEntryResponse]:
        hits = self.vector_store.query(
            query_text=query,
            n_results=n_results,
        )
        entry_ids = [h["entry_id"] for h in hits]
        if not entry_ids:
            return []
        result = await self.session.execute(
            select(models.MemoryEntry).where(models.MemoryEntry.id.in_(entry_ids))
        )
        entries = {e.id: e for e in result.scalars().all()}
        return [schemas.MemoryEntryResponse.model_validate(entries[eid])
                for eid in entry_ids if eid in entries]

    async def get_agent_memories(
        self, agent_id: str, limit: int = 20
    ) -> List[models.MemoryEntry]:
        result = await self.session.execute(
            select(models.MemoryEntry)
            .where(models.MemoryEntry.agent_id == agent_id)
            .order_by(desc(models.MemoryEntry.created_at))
            .limit(limit)
        )
        return result.scalars().all()
