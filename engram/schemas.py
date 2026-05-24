from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MemoryEntryBase(BaseModel):
    type: str
    title: str
    content: str
    tags: list[str] = []
    references: list[str] = []
    source_file: str

class MemoryEntryCreate(MemoryEntryBase):
    pass

class MemoryEntryResponse(MemoryEntryBase):
    id: int
    created_at: datetime
    compacted_into: int | None

    model_config = ConfigDict(from_attributes=True)

class CompactionIndexBase(BaseModel):
    entry_id: int
    merged_ids: list[int]

class CompactionIndexCreate(CompactionIndexBase):
    pass

class CompactionIndexResponse(CompactionIndexBase):
    id: int
    compacted_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SnapshotIndexBase(BaseModel):
    entry_ids: list[int]
    memory_md_hash: str

class SnapshotIndexCreate(SnapshotIndexBase):
    pass

class SnapshotIndexResponse(SnapshotIndexBase):
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class SessionStartContext(BaseModel):
    recent_memories: list[MemoryEntryResponse]
    # MVP: only holds recent memories (could add missions later).

class MessageContext(BaseModel):
    relevant_memories: list[MemoryEntryResponse]
