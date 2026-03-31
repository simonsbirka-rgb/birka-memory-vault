from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from . import models, schemas

class MemoryEventManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_memory_entry(self, entry: schemas.MemoryEntryCreate) -> models.MemoryEntry:
        db_entry = models.MemoryEntry(
            type=entry.type,
            title=entry.title,
            content=entry.content,
            tags=entry.tags,
            references=entry.references,
            source_file=entry.source_file
        )
        self.session.add(db_entry)
        await self.session.commit()
        await self.session.refresh(db_entry)
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
