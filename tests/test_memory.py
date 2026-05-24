"""Tests for engram.events — memory entry CRUD."""


import pytest
from sqlalchemy import select

from engram.events import MemoryEventManager
from engram.models import MemoryEntry
from engram.schemas import MemoryEntryCreate, SnapshotIndexCreate


@pytest.mark.asyncio
async def test_add_memory_entry_commits(session):
    """add_memory_entry writes, commits, and returns the record."""
    manager = MemoryEventManager(session)

    raw = MemoryEntryCreate(
        type="decision",
        title="Switch to Gemini for ACP",
        content="Switched from failing Qwen subagents to Gemini ACP runtime.",
        tags=["decision", "infrastructure", "acp"],
        references=[],
        source_file="memory/2026-03-29.md",
    )
    entry = await manager.add_memory_entry(raw)

    assert entry.id is not None
    assert entry.title == raw.title
    assert entry.type == raw.type
    assert entry.tags == list(raw.tags)
    assert entry.source_file == raw.source_file
    assert entry.created_at is not None


@pytest.mark.asyncio
async def test_get_entries_by_tag(session):
    """get_entries_by_tag filters by matching tag."""
    manager = MemoryEventManager(session)

    created = [
        MemoryEntry(
            type="observation",
            title=f"Note {i}",
            content=f"Content {i}",
            tags=["python", "async"] if i % 2 == 0 else ["db", "sqlite"],
            references=[],
            source_file=f"memory/{i}.md",
        )
        for i in range(5)
    ]
    session.add_all(created)
    await session.commit()

    result = await manager.get_entries_by_tag("python")
    assert len(result) == 3
    assert all("python" in e.tags for e in result)


@pytest.mark.asyncio
async def test_compact_entries_commits_once(session):
    """compact_entries writes merged entry and posts one compaction index."""
    manager = MemoryEventManager(session)

    old = [
        MemoryEntry(
            type="observation",
            title=f"Seed {i}",
            content=f"Seed content {i}",
            tags=["seed"],
            references=[],
            source_file=f"seed/{i}.md",
        )
        for i in range(2)
    ]
    session.add_all(old)
    await session.commit()
    old_ids = [e.id for e in old]

    merged = MemoryEntryCreate(
        type="summary",
        title="Merged summary",
        content="Combined content of two seeds.",
        tags=["summary", "merged"],
        references=[],
        source_file="seed/merged.md",
    )
    compaction = await manager.compact_entries(merged, old_ids)

    assert compaction.id is not None
    assert compaction.merged_ids == old_ids
    assert compaction.entry_id is not None

    stmt = select(MemoryEntry).where(MemoryEntry.id.in_(old_ids))
    result = await session.execute(stmt)
    updated = result.scalars().all()
    assert all(e.compacted_into == compaction.entry_id for e in updated)


@pytest.mark.asyncio
async def test_create_snapshot_commits(session):
    """create_snapshot persists a snapshot index in a single commit."""
    manager = MemoryEventManager(session)

    snap = await manager.create_snapshot(
        SnapshotIndexCreate(
            entry_ids=[1, 2, 3],
            memory_md_hash="abcdef0123456789" * 4,
        )
    )

    assert snap.id is not None
    assert snap.entry_ids == [1, 2, 3]
    assert snap.timestamp is not None
