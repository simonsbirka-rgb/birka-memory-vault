# Engram: Structured Memory Index for AI Agents

<p align="center">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0-red?style=for-the-badge&logo=sqlalchemy" alt="SQLAlchemy 2.0" />
  <img src="https://img.shields.io/badge/Pydantic-2.0-blue?style=for-the-badge&logo=pydantic" alt="Pydantic 2.0" />
  <img src="https://img.shields.io/badge/FastAPI-Compatible-009688?style=for-the-badge&logo=fastapi" alt="FastAPI Compatible" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License" />
</p>

**Engram** is an enterprise-grade, asynchronous structured memory index and context-retrieval engine for autonomous AI agents and multi-agent systems. It builds on **SQLAlchemy 2.0 async** and **Pydantic v2** to provide agents with a queryable, durable record of their reasoning history—decisions, observations, lessons learned, and snapshots.

Developed and maintained by [svprojects.lt](https://svprojects.lt).

---

## 🎯 Primary Use Case: Complex & Semantic AI Systems (Legal, Medical, Enterprise)

In high-complexity domains like **Law**, **Compliance**, and **Enterprise Decision Management**, meaning and context must be strictly ordered, auditable, and easily accessible. 

General LLM conversational histories quickly degrade or saturate the context window with conversational noise. **Engram** solves this by modeling memory as a structured, tag-filtered, compactable index.

### Why Engram?
- **⚖️ Legal & Medical Compliance**: Keep absolute, immutable, and auditable records of every agentic decision, tool execution, and milestone.
- **🧠 Semantic Compaction**: Automatically compact historical, verbose execution steps into structured, high-level summaries without losing core context.
- **⚡ SQL-Level JSON Filtering**: Retrieve context with micro-second latencies using Postgres/SQLite JSONB tag and reference arrays—bypassing expensive vector DB lookups for exact-match semantic groups.
- **🕸️ Graph-Like Agent Fleets**: Track parent-child relationships, agent spawn states, commands, and safeguards within a structured transactional database.

---

## 🏗️ Architectural Flow

```
                        ┌───────────┐
                        │ Raw Notes │  Markdown files, raw LLM observations
                        └─────┬─────┘
                              │ Event-driven emitter
                              ▼
                  ┌───────────────────────┐
                  │        Engram         │
                  │ ───────────────────── │
                  │ Session | Hooks | ORM │
                  └───────────┬───────────┘
                              │ SQLAlchemy 2.0 (Async)
                              ▼
                   ┌─────────────────────┐
                   │  SQLite/PostgresDB  │  Structured tables + JSONB indexing
                   └─────────────────────┘
```

---

## 📦 Features & Layers

| Layer | Module | Responsibility |
|---|---|---|
| **Schema** | `engram.schemas` | Highly validated Pydantic DTOs for type-safe data validation. |
| **ORM** | `engram.models` | SQLAlchemy 2.0 async declarative models, enums, and indexes. |
| **Events** | `engram.events` | `MemoryEventManager` — creation, snapshotting, and transaction compaction. |
| **Hooks** | `engram.hooks` | `MemoryRetrievalHooks` — session-start and per-message context generation. |
| **Database** | `engram.database` | Database singletons for `engine` and `AsyncSessionLocal` setups. |

---

## ⚡ Quickstart

### 1. Installation

Ensure you have your environment ready:
```bash
pip install engram-layer
```
*(Dependencies: `sqlalchemy>=2.0.0`, `pydantic>=2.0.0`, `alembic>=1.12.0`)*

### 2. Tables & Session Setup
```python
from engram import engine, Base

# Create tables idempotently on startup
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

### 3. Write a Memory Entry (Events)
Log critical decisions and audit milestones during runtime:
```python
from engram.events import MemoryEventManager
from engram.schemas import MemoryEntryCreate
from engram import AsyncSessionLocal

async with AsyncSessionLocal() as session:
    mgr = MemoryEventManager(session)
    entry = await mgr.add_memory_entry(
        MemoryEntryCreate(
            type="decision",
            title="Use PostgreSQL for semantic search",
            content="PGVector allows unified SQL querying with relational assets.",
            tags=["infrastructure", "legal-ai", "postgres"],
            references=["LITEKO-decision-2026"],
            source_file="memory/2026-05-24.md",
        )
    )
```

### 4. Retrieve Context (Hooks)
Inject memories back into the agent's system prompt during a new session, or dynamically filter on incoming user queries:
```python
from engram.hooks import MemoryRetrievalHooks
from engram import AsyncSessionLocal

async with AsyncSessionLocal() as session:
    hooks = MemoryRetrievalHooks(session)

    # A. Session-start hook: grab the 10 most recent memories to re-orient the agent
    start_ctx = await hooks.session_start_hook(limit=10)

    # B. Per-message hook: inject context dynamically matching incoming queries or tags
    msg_ctx = await hooks.per_message_hook(tags=["infrastructure"], limit=5)
```

### 5. Memory Compaction
Consolidate thousands of operational step logs into a single high-level summary to prevent context window bloat:
```python
async with AsyncSessionLocal() as session:
    mgr = MemoryEventManager(session)
    compaction = await mgr.compact_entries(
        merged_entry=MemoryEntryCreate(
            type="summary",
            title="Compacted May 2026 Infrastructure Decisions",
            content="We officially migrated and tested our pgvector configuration...",
            tags=["summary", "infrastructure"],
            references=[],
            source_file="memory/2026-05-24.md",
        ),
        old_entry_ids=[1, 2, 3],  # IDs of the detailed step entries
    )
```

---

## 🛡️ License

Engram is licensed under the [MIT License](LICENSE).

Developed with precision by [svprojects.lt](https://svprojects.lt). For partnership inquiries or semantic system design services, reach out to our core team.
