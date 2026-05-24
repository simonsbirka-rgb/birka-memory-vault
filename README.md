# Engram

**Engram** is a structured, queryable memory index for AI agents. It builds on
SQLAlchemy 2.0 async and Pydantic to give every agent session a durable,
searchable record of its reasoning history — decisions, lessons learned,
compaction outcomes, and snapshots.

```
                        ┌──────────┐
                        │ markdown │  raw notes, .md files
                        └────┬─────┘
                             │ event emitter
                             ▼
                  ┌───────────────────────┐
                  │   engram  (this lib)   │
                  │ ─────────────────────  │
                  │ Session | Hooks | ORM  │
                  └─────────┬─────────────┘
                            │ SQLAlchemy
                            ▼
                   ┌──────────────────┐
                   │  SQLite /         │
                   │  PostgreSQL        │
                   └──────────────────┘
```

## Layers

| Layer | Module | Responsibility |
|---|---|---|
| Schema | `engram.schemas` | Pydantic DTOs for all inbound/outbound data |
| ORM | `engram.models` | SQLAlchemy 2.0 declarative models + enums |
| Events | `engram.events` | `MemoryEventManager` — create entries, compact, snapshot |
| Hooks | `engram.hooks` | `MemoryRetrievalHooks` — session-start and per-message context |
| DB | `engram.database` | Eager singletons: `engine`, `AsyncSessionLocal` |

## Quick-start

```python
# 1. Engine / session — the consuming app owns session lifecycle
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from engram import engine, AsyncSessionLocal  # optional convenience re-exports

# Tables are created idempotently on first use
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)

# 2. Write a memory entry
from engram.events import MemoryEventManager
from engram.schemas import MemoryEntryCreate

async with AsyncSessionLocal() as session:
    mgr = MemoryEventManager(session)
    entry = await mgr.add_memory_entry(
        MemoryEntryCreate(
            type="decision",
            title="Use PostgreSQL for vector search",
            content="Neon Postgres gives pgvector out of the box.",
            tags=["decision", "infrastructure", "db"],
            references=[],
            source_file="memory/2026-05-24.md",
        )
    )

# 3. Retrieve context
from engram.hooks import MemoryRetrievalHooks

async with AsyncSessionLocal() as session:
    hooks = MemoryRetrievalHooks(session)

    # 3a — at session start
    ctx = await hooks.session_start_hook(limit=10)

    # 3b — per user message (SQL-level JSON tag filtering)
    ctx = await hooks.per_message_hook(tags=["infrastructure"], limit=5)

# 4. Compact old entries into one summary
async with AsyncSessionLocal() as session:
    mgr = MemoryEventManager(session)
    compaction = await mgr.compact_entries(
        merged_entry=MemoryEntryCreate(
            type="summary",
            title="May 2026 decisions",
            content="…",
            tags=["summary"],
            references=[],
            source_file="memory/2026-05-24.md",
        ),
        old_entry_ids=[1, 2, 3],
    )

# 5. Snapshot the registry
async with AsyncSessionLocal() as session:
    mgr = MemoryEventManager(session)
    snap = await mgr.create_snapshot(
        SnapshotIndexCreate(
            entry_ids=[1, 2, 3],
            memory_md_hash="sha256-hash-of-memory-md",
        )
    )
```

## Database backends

| Layer | Dev | Prod |
|---|---|---|
| Engine | SQLite (`aiosqlite`) | PostgreSQL (`asyncpg`) |
| Configure | default (no env needed) | `DATABASE_URL=postgresql+asyncpg://…` |

## Installation

```bash
pip install .[dev]   # library + pytest-asyncio + ruff + black
```

## Requirements

- Python ≥ 3.11
- SQLAlchemy ≥ 2.0
- Pydantic ≥ 2.0

## Architecture

```
markdown files  ──emit──►  event handlers  ──ORM──►  database
                     │
                     ▼
              MemoryEntry  ── tagged JSON
              CompactionIndex  ── merge trace
              SnapshotIndex  ── restore points
```

The consuming application is responsible for:
- Creating the engine and session.
- Calling `Base.metadata.create_all` at startup.
- Committing transactions to match its own consistency requirements.

Engram does **not** call `get_db()` or `init_db()` internally — those
concerns live in the application layer, not the library.
