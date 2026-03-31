from typing import List, Optional
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Boolean,
    Float,
    Index,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    pass


# --- Enums for typed fields ---


class NodeType(str, Enum):
    AGENT = "agent"
    MISSION = "mission"
    ARTIFACT = "artifact"
    MEMORY = "memory"
    CONTEXT = "context"
    TASK = "task"
    FILE = "file"
    USER = "user"


class EdgeType(str, Enum):
    SPAWNED_BY = "SPAWNED_BY"
    PRODUCES = "PRODUCES"
    REQUIRES = "REQUIRES"
    REFERENCES = "REFERENCES"
    CONTAINS = "CONTAINS"
    DERIVED_FROM = "DERIVED_FROM"
    BLOCKS = "BLOCKS"
    DEPENDS_ON = "DEPENDS_ON"


class MissionStatus(str, Enum):
    DISPATCHED = "dispatched"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    OVERRIDE = "override"


class FleetStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    PAUSED = "paused"
    DRAINING = "draining"
    DEAD = "dead"
    FAILED = "failed"


class CommandType(str, Enum):
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    KILL = "KILL"
    OVERRIDE_MODEL = "OVERRIDE_MODEL"
    SET_PRIORITY = "SET_PRIORITY"
    DRAIN = "DRAIN"
    SYNC = "SYNC"


class SafeguardType(str, Enum):
    MAX_DEPTH_EXCEEDED = "MAX_DEPTH_EXCEEDED"
    LOOP_DETECTED = "LOOP_DETECTED"
    COST_CEILING = "COST_CEILING"
    TIMEOUT = "TIMEOUT"
    ERROR_RATE = "ERROR_RATE"
    MANUAL_KILL = "MANUAL_KILL"


class EventCategory(str, Enum):
    SPAWN = "spawn"
    DISPATCH = "dispatch"
    COMMAND = "command"
    SAFEGUARD = "safeguard"
    STATE_CHANGE = "state_change"
    ERROR = "error"
    METRIC = "metric"


# --- Original 3 tables (preserved) ---


class MemoryEntry(Base):
    __tablename__ = "memory_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSON)
    references: Mapped[list[str]] = mapped_column(JSON)
    source_file: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    compacted_into: Mapped[Optional[int]] = mapped_column(
        ForeignKey("memory_entry.id"), nullable=True
    )


class CompactionIndex(Base):
    __tablename__ = "compaction_index"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("memory_entry.id"))
    merged_ids: Mapped[list[int]] = mapped_column(JSON)
    compacted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SnapshotIndex(Base):
    __tablename__ = "snapshot_index"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    entry_ids: Mapped[list[int]] = mapped_column(JSON)
    memory_md_hash: Mapped[str] = mapped_column(String(64))


# --- OpenClaw v2 Orchestrator Tables ---


class Node(Base):
    """Universal entity store for agents, missions, artifacts, memory, context."""

    __tablename__ = "nodes"
    __table_args__ = (
        Index("idx_nodes_type", "type"),
        Index("idx_nodes_type_status", "type", "status"),
        Index("idx_nodes_created", "created_at"),
        Index("idx_nodes_properties", "properties", postgresql_using="gin"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[NodeType] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    properties: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("nodes.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    parent: Mapped[Optional["Node"]] = relationship(
        "Node", remote_side="Node.id", back_populates="children"
    )
    children: Mapped[List["Node"]] = relationship("Node", back_populates="parent")
    outgoing_edges: Mapped[List["Edge"]] = relationship(
        "Edge", foreign_keys="Edge.source_id", back_populates="source"
    )
    incoming_edges: Mapped[List["Edge"]] = relationship(
        "Edge", foreign_keys="Edge.target_id", back_populates="target"
    )


class Edge(Base):
    """Typed relationships between nodes."""

    __tablename__ = "edges"
    __table_args__ = (
        Index("idx_edges_type", "type"),
        Index("idx_edges_source", "source_id"),
        Index("idx_edges_target", "target_id"),
        Index("idx_edges_source_type", "source_id", "type"),
        Index("idx_edges_target_type", "target_id", "type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("nodes.id"), nullable=False
    )
    target_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("nodes.id"), nullable=False
    )
    type: Mapped[EdgeType] = mapped_column(String(20), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    properties: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    source: Mapped["Node"] = relationship(
        "Node", foreign_keys=[source_id], back_populates="outgoing_edges"
    )
    target: Mapped["Node"] = relationship(
        "Node", foreign_keys=[target_id], back_populates="incoming_edges"
    )


class Mission(Base):
    """Work units dispatched from OpenClaw to Birka."""

    __tablename__ = "missions"
    __table_args__ = (
        Index("idx_missions_status", "status"),
        Index("idx_missions_birka", "birka_instance_id"),
        Index("idx_missions_dispatched", "dispatched_at"),
        Index("idx_missions_priority_status", "priority", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    node_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("nodes.id"), unique=True, nullable=False
    )
    openclaw_id: Mapped[str] = mapped_column(String(64), nullable=False)
    birka_instance_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[MissionStatus] = mapped_column(String(20), default="dispatched")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    dispatched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    node: Mapped["Node"] = relationship("Node", foreign_keys=[node_id])


class BirkaFleet(Base):
    """All active/dead Birka instances."""

    __tablename__ = "birka_fleet"
    __table_args__ = (
        Index("idx_fleet_status", "status"),
        Index("idx_fleet_node", "node_id"),
        Index("idx_fleet_last_heartbeat", "last_heartbeat"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    node_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("nodes.id"), unique=True, nullable=False
    )
    pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[FleetStatus] = mapped_column(String(20), default="active")
    capabilities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    spawn_depth: Mapped[int] = mapped_column(Integer, default=0)
    parent_instance_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("birka_fleet.id"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    terminated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    node: Mapped["Node"] = relationship("Node", foreign_keys=[node_id])
    parent: Mapped[Optional["BirkaFleet"]] = relationship(
        "BirkaFleet", remote_side="BirkaFleet.id", back_populates="children"
    )
    children: Mapped[List["BirkaFleet"]] = relationship(
        "BirkaFleet", back_populates="parent"
    )


class SpawnTree(Base):
    """Every spawn event with depth tracking for recursion limits."""

    __tablename__ = "spawn_tree"
    __table_args__ = (
        Index("idx_spawn_parent", "parent_instance_id"),
        Index("idx_spawn_child", "child_instance_id"),
        Index("idx_spawn_depth", "depth"),
        Index("idx_spawn_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_instance_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("birka_fleet.id"), nullable=False
    )
    child_instance_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("birka_fleet.id"), nullable=False
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    context_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    spawn_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mission_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("missions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    parent: Mapped["BirkaFleet"] = relationship(
        "BirkaFleet", foreign_keys=[parent_instance_id]
    )
    child: Mapped["BirkaFleet"] = relationship(
        "BirkaFleet", foreign_keys=[child_instance_id]
    )
    mission: Mapped[Optional["Mission"]] = relationship(
        "Mission", foreign_keys=[mission_id]
    )


class ResourceManifest(Base):
    """Birka's declared capabilities parsed from TOOLS.md/SOUL.md."""

    __tablename__ = "resource_manifest"
    __table_args__ = (
        Index("idx_manifest_instance", "instance_id"),
        Index("idx_manifest_capability", "capability_name"),
        UniqueConstraint(
            "instance_id", "capability_name", name="uq_instance_capability"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("birka_fleet.id"), nullable=False
    )
    capability_name: Mapped[str] = mapped_column(String(100), nullable=False)
    capability_type: Mapped[str] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    constraints: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    declared_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    instance: Mapped["BirkaFleet"] = relationship(
        "BirkaFleet", foreign_keys=[instance_id]
    )


class ControlCommand(Base):
    """Signed commands from OpenClaw to Birka (PAUSE, KILL, OVERRIDE_MODEL)."""

    __tablename__ = "control_commands"
    __table_args__ = (
        Index("idx_commands_target", "target_instance_id"),
        Index("idx_commands_status", "status"),
        Index("idx_commands_type", "command_type"),
        Index("idx_commands_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    target_instance_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("birka_fleet.id"), nullable=False
    )
    command_type: Mapped[CommandType] = mapped_column(String(20), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    signature: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    target: Mapped["BirkaFleet"] = relationship(
        "BirkaFleet", foreign_keys=[target_instance_id]
    )


class SafeguardEvent(Base):
    """Circuit breaker fires (loops, depth exceeded, cost ceiling)."""

    __tablename__ = "safeguard_events"
    __table_args__ = (
        Index("idx_safeguard_instance", "instance_id"),
        Index("idx_safeguard_type", "safeguard_type"),
        Index("idx_safeguard_severity", "severity"),
        Index("idx_safeguard_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("birka_fleet.id"), nullable=False
    )
    mission_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("missions.id"), nullable=True
    )
    safeguard_type: Mapped[SafeguardType] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    action_taken: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    instance: Mapped["BirkaFleet"] = relationship(
        "BirkaFleet", foreign_keys=[instance_id]
    )
    mission: Mapped[Optional["Mission"]] = relationship(
        "Mission", foreign_keys=[mission_id]
    )


class Event(Base):
    """Append-only audit log for all orchestrator events."""

    __tablename__ = "events"
    __table_args__ = (
        Index("idx_events_category", "category"),
        Index("idx_events_source", "source_id"),
        Index("idx_events_created", "created_at"),
        Index("idx_events_category_source", "category", "source_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[EventCategory] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
