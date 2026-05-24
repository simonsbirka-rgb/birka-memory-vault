"""Tests for engram.hooks — session-start and per-message memory retrieval."""

import pytest

from engram.hooks import MemoryRetrievalHooks
from engram.models import MemoryEntry


@pytest.mark.asyncio
async def test_session_start_hook(session):
    """session_start_hook returns the N most recent entries."""
    hooks = MemoryRetrievalHooks(session)

    entries = [
        MemoryEntry(
            type="observation",
            title=f"Entry {i}",
            content=f"Content {i}",
            tags=["hook", "test"],
            references=[],
            source_file=f"memory/{i}.md",
        )
        for i in range(5)
    ]
    session.add_all(entries)
    await session.commit()

    ctx = await hooks.session_start_hook(limit=3)
    assert len(ctx.recent_memories) == 3


@pytest.mark.asyncio
async def test_session_start_hook_empty_db(session):
    """session_start_hook on an empty DB returns an empty list."""
    hooks = MemoryRetrievalHooks(session)
    ctx = await hooks.session_start_hook(limit=5)
    assert ctx.recent_memories == []


@pytest.mark.asyncio
async def test_per_message_hook_tag_filter(session):
    """per_message_hook returns entries whose JSON tags array includes the query tag."""
    hooks = MemoryRetrievalHooks(session)

    entries = [
        MemoryEntry(
            type="decision",
            title="Use asyncio",
            content="Asyncio is great.",
            tags=["python", "async"],
            references=[],
            source_file="memory/1.md",
        ),
        MemoryEntry(
            type="observation",
            title="Postgres issue",
            content="Connection pool full.",
            tags=["db", "postgres"],
            references=[],
            source_file="memory/2.md",
        ),
    ]
    session.add_all(entries)
    await session.commit()

    ctx = await hooks.per_message_hook(tags=["python"], limit=5)
    assert len(ctx.relevant_memories) >= 1
    assert any(m.title == "Use asyncio" for m in ctx.relevant_memories)
    assert not any(m.title == "Postgres issue" for m in ctx.relevant_memories)


@pytest.mark.asyncio
async def test_per_message_hook_no_tags_fallback(session):
    """per_message_hook with no tags returns the most recent entries."""
    hooks = MemoryRetrievalHooks(session)

    entries = [
        MemoryEntry(
            type="observation",
            title=f"Note {i}",
            content=f"Content {i}",
            tags=["generic"],
            references=[],
            source_file=f"memory/{i}.md",
        )
        for i in range(3)
    ]
    session.add_all(entries)
    await session.commit()

    ctx = await hooks.per_message_hook(limit=2)
    assert len(ctx.relevant_memories) == 2


@pytest.mark.asyncio
async def test_per_message_hook_tag_no_match(session):
    """If no entries match the tag, per_message_hook falls back to most recent."""
    hooks = MemoryRetrievalHooks(session)

    session.add(
        MemoryEntry(
            type="note",
            title="Only entry",
            content="Content.",
            tags=["x"],
            references=[],
            source_file="memory/x.md",
        )
    )
    await session.commit()

    ctx = await hooks.per_message_hook(tags=["nonexistent"], limit=3)
    assert len(ctx.relevant_memories) >= 1
