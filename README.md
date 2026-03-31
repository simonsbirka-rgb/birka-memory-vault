# Birka Memory Vault

A structured, queryable memory index as a layer on top of Birka's existing markdown memory system.

This repository provides an async SQLAlchemy 2.0 system that acts as an index over markdown files. It does not replace the raw markdown files but adds structured querying capabilities, references, tags, and tracking of compactions/snapshots.

## Features
- **SQLAlchemy 2.0 Async:** Non-blocking database interactions.
- **SQLite (Dev) / PostgreSQL (Prod):** Configurable via `DATABASE_URL`.
- **Pydantic Schemas:** Strong typing for input/output events.
- **Alembic Migrations:** Versioned database schemas.
- **Event-Based Writes:** Handlers to insert/compact entries when memories are formed or summarized.

## Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run Alembic migrations to set up the database schema:
   ```bash
   alembic upgrade head
   ```

## Structure
- `birka_memory_vault/models.py`: Declarative ORM models.
- `birka_memory_vault/schemas.py`: Pydantic validation models.
- `birka_memory_vault/database.py`: Async engine configuration.
- `birka_memory_vault/events.py`: Handlers for storing and compacting memory.
