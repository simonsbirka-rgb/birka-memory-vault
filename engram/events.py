
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas

# Type aliases to keep signatures within 88 chars
_EntryCreate = schemas.MemoryEntryCreate
_EntryType = models.MemoryEntry
_SnapType = models.SnapshotIndex


class MemoryEventManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _add_memory_entry(
        self, entry: _EntryCreate
    ) -> _EntryType:
        """Internal helper: add + flush only. The caller owns commit."""
        db_entry = models.MemoryEntry(
            type=entry.type,
            title=entry.title,
            content=entry.content,
            tags=entry.tags,
            references=entry.references,
            source_file=entry.source_file,
        )
        self.session.add(db_entry)
        await self.session.flush()
        return db_entry

    async def add_memory_entry(
        self, entry: _EntryCreate
    ) -> _EntryType:
        """Persist a single memory entry and commit immediately."""
        db_entry = await self._add_memory_entry(entry)
        await self.session.commit()
        await self.session.refresh(db_entry)
        return db_entry

    async def get_entries_by_tag(self, tag: str) -> list[_EntryType]:
        result = await self.session.execute(select(models.MemoryEntry))
        entries = result.scalars().all()
        return [e for e in entries if tag in e.tags]

    async def compact_entries(
        self, merged_entry: _EntryCreate, old_entry_ids: list[int]
    ) -> models.CompactionIndex:
        """Merge old entries into a new one. Owns the single commit+refresh."""
        new_entry = await self._add_memory_entry(merged_entry)

        result = await self.session.execute(
            select(models.MemoryEntry).where(
                models.MemoryEntry.id.in_(old_entry_ids)
            )
        )
        old_entries = result.scalars().all()
        for e in old_entries:
            e.compacted_into = new_entry.id

        compaction = models.CompactionIndex(
            entry_id=new_entry.id,
            merged_ids=old_entry_ids,
        )
        self.session.add(compaction)

        # Single commit + refresh (sole owner)
        await self.session.commit()
        await self.session.refresh(compaction)
        return compaction

    async def create_snapshot(
        self, snapshot: schemas.SnapshotIndexCreate
    ) -> _SnapType:
        """Persist a snapshot index. Owns the single commit+refresh."""
        db_snapshot = models.SnapshotIndex(
            entry_ids=snapshot.entry_ids,
            memory_md_hash=snapshot.memory_md_hash,
        )
        self.session.add(db_snapshot)

        # Single commit + refresh (sole owner)
        await self.session.commit()
        await self.session.refresh(db_snapshot)
        return db_snapshot
