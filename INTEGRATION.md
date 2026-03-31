# Integration Guide

This guide explains how to integrate the Birka Memory Vault into Birka's daily workflows.

## Concept
Birka currently writes raw Markdown strings to `memory/YYYY-MM-DD.md`.
The **Vault** acts as a structured parallel layer. When Birka creates or summarizes a memory in MD format, it emits an event to log the entry in the Vault.

## Workflow

### 1. Initializing the Vault
In Birka's startup or session configuration:
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from birka_memory_vault.database import AsyncSessionLocal, init_db
from birka_memory_vault.events import MemoryEventManager

# Ensure the database schemas exist
await init_db()
```

### 2. Emitting Memory Events
Whenever Birka makes a decision, logs an action, or learns a lesson, run a background task to record the event:

```python
from birka_memory_vault.schemas import MemoryEntryCreate

async def log_birka_event(type: str, title: str, content: str, source_file: str, tags: list):
    async with AsyncSessionLocal() as session:
        manager = MemoryEventManager(session)
        entry = MemoryEntryCreate(
            type=type,
            title=title,
            content=content,
            tags=tags,
            source_file=source_file
        )
        await manager.add_memory_entry(entry)
```

### 3. Compaction
When daily logs are reviewed and compiled into `MEMORY.md` (the curated wisdom), call the compaction handler to logically merge entries without losing traceability:

```python
async def perform_compaction(merged_entry_data: MemoryEntryCreate, old_entry_ids: list[int]):
    async with AsyncSessionLocal() as session:
        manager = MemoryEventManager(session)
        compaction = await manager.compact_entries(merged_entry_data, old_entry_ids)
        return compaction
```

### 4. Snapshots
Create a snapshot of the current state of tracked memory to easily restore or re-index:

```python
from birka_memory_vault.schemas import SnapshotIndexCreate

async def take_snapshot(entry_ids: list[int], md_hash: str):
    async with AsyncSessionLocal() as session:
        manager = MemoryEventManager(session)
        snapshot_data = SnapshotIndexCreate(
            entry_ids=entry_ids,
            memory_md_hash=md_hash
        )
        await manager.create_snapshot(snapshot_data)
```

## Production vs Dev
Set `DATABASE_URL` in the environment to connect to PostgreSQL in production:
```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/birka_memory"
```
Without the variable, it defaults to a local `sqlite+aiosqlite:///./birka_memory.db` file.