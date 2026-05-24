# Quick-start — Engram

## 1. Install

```bash
pip install .[dev]
```

## 2. Initialise the schema

```python
from sqlalchemy.ext.asyncio import create_async_engine
from engram.models import Base
from engram.database import AsyncSessionLocal

engine = create_async_engine("sqlite+aiosqlite:///./engram_dev.db")

async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

## 3. Log an event

```python
from engram.events import MemoryEventManager
from engram.schemas import MemoryEntryCreate

async with AsyncSessionLocal() as session:
    mgr = MemoryEventManager(session)
    entry = await mgr.add_memory_entry(
        MemoryEntryCreate(
            type="decision",
            title="Adopt Engram",
            content="…",
            tags=["decision"],
            references=[],
            source_file="memory/2026-05-24.md",
        )
    )
```

## 4. Retrieve context

```python
from engram.hooks import MemoryRetrievalHooks

async with AsyncSessionLocal() as session:
    hooks = MemoryRetrievalHooks(session)

    # Start of session — most recent entries
    ctx = await hooks.session_start_hook(limit=10)

    # Per-message — SQL-level JSON tag filtering
    ctx = await hooks.per_message_hook(tags=["decision"], limit=5)
```

## 5. Compaction and snapshots

```python
async with AsyncSessionLocal() as session:
    mgr = MemoryEventManager(session)
    compaction = await mgr.compact_entries(merged_entry=..., old_entry_ids=[1, 2, 3])
    snap = await mgr.create_snapshot(SnapshotIndexCreate(entry_ids=[1, 2, 3], ...))
```

## Session management

Engram is a **library-only** package. It does **not** manage sessions or
transaction boundaries for you. The consuming application must:

1. Create `engine` and `AsyncSessionLocal` (or build its own).
2. Call `Base.metadata.create_all` once at startup.
3. Open a session with `AsyncSessionLocal()` and pass it into
   `MemoryEventManager` / `MemoryRetrievalHooks`.
