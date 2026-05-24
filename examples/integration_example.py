"""
Integration example — Engram library used end-to-end.

Run with:
    python examples/integration_example.py

Prerequisites
-------------
1. Install the package:
       pip install .[dev]
2. engram_dev.db is auto-created at the repo root on first run.
"""

import asyncio

from engram import AsyncSessionLocal, engine
from engram.events import MemoryEventManager
from engram.hooks import MemoryRetrievalHooks
from engram.models import Base
from engram.schemas import MemoryEntryCreate, SnapshotIndexCreate


async def ensure_schema() -> None:
    """Create all tables if they do not yet exist (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main() -> None:
    await ensure_schema()
    saved_id = "demo-entry-id"

    # ── 1. Write a memory entry ────────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        mgr = MemoryEventManager(session)
        entry = MemoryEntryCreate(
            type="decision",
            title="Adopt Engram for memory indexing",
            content="Switched from raw markdown files "
            "to structured SQLAlchemy-backed memory.",
            tags=["decision", "engram", "infrastructure"],
            references=[],
            source_file="memory/2026-05-24.md",
        )
        saved = await mgr.add_memory_entry(entry)
        saved_id = saved.id
        print(f"  Saved entry id={saved.id}  title={saved.title!r}")

    # ── 2. Session-start hook ──────────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        hooks = MemoryRetrievalHooks(session)
        ctx = await hooks.session_start_hook(limit=10)
        print(f"  session_start_hook  ->  {len(ctx.recent_memories)} memories")

    # ── 3. Per-message hook (tag filter) ───────────────────────────────────
    async with AsyncSessionLocal() as session:
        hooks = MemoryRetrievalHooks(session)
        msg_ctx = await hooks.per_message_hook(
            tags=["engram", "infrastructure"],
            limit=5,
        )
        for mem in msg_ctx.relevant_memories:
            print(
                f"    [{mem.created_at:%Y-%m-%d %H:%M}]  {mem.title}"
            )

    # ── 4. compact_entries ─────────────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        mgr = MemoryEventManager(session)
        merged = MemoryEntryCreate(
            type="summary",
            title="Consolidated Engram migration notes",
            content="Combined outcome of "
            "migrating from raw markdown to Engram.",
            tags=["summary", "engram", "infrastructure"],
            references=[],
            source_file="memory/2026-05-24.md",
        )
        compaction = await mgr.compact_entries(
            merged_entry=merged,
            old_entry_ids=[saved_id],
        )
        print(f"  compact_entries  ->  new entry id={compaction.entry_id}")

    # ── 5. create_snapshot ─────────────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        mgr = MemoryEventManager(session)
        snap = await mgr.create_snapshot(
            SnapshotIndexCreate(
                entry_ids=[saved_id],
                memory_md_hash="demo-example-hash",
            )
        )
        print(f"  create_snapshot  ->  id={snap.id}")

    print("\nDone -- engram_dev.db written to the repo root.")


if __name__ == "__main__":
    asyncio.run(main())
