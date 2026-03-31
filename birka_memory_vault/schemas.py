from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

class MemoryEntryBase(BaseModel):
    type: str
    title: str
    content: str
    tags: List[str] = []
    references: List[str] = []
    source_file: str

class MemoryEntryCreate(MemoryEntryBase):
    pass

class MemoryEntryResponse(MemoryEntryBase):
    id: int
    created_at: datetime
    compacted_into: Optional[int]

    model_config = ConfigDict(from_attributes=True)

class CompactionIndexBase(BaseModel):
    entry_id: int
    merged_ids: List[int]

class CompactionIndexCreate(CompactionIndexBase):
    pass

class CompactionIndexResponse(CompactionIndexBase):
    id: int
    compacted_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SnapshotIndexBase(BaseModel):
    entry_ids: List[int]
    memory_md_hash: str

class SnapshotIndexCreate(SnapshotIndexBase):
    pass

class SnapshotIndexResponse(SnapshotIndexBase):
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
