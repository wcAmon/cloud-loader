"""Database models using SQLModel."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class Backup(SQLModel, table=True):
    """Backup table for storing upload metadata."""

    __tablename__ = "backups"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=6)
    file_path: str
    file_size: int
    uploaded_at: datetime = Field(default_factory=_utc_now)
    expires_at: datetime


class User(SQLModel, table=True):
    """User table for API key authentication."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(unique=True, index=True, max_length=20)  # usr_xxx
    api_key: str = Field(unique=True, index=True, max_length=40)  # ll_xxx...
    created_at: datetime = Field(default_factory=_utc_now)


class MdStorage(SQLModel, table=True):
    """MD file storage for agents - publicly accessible, no expiration."""

    __tablename__ = "md_storage"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=6)

    # MD Content
    content: str
    content_size: int

    # MD Metadata
    filename: str = Field(max_length=100)  # e.g., my-skill.md, setup-guide.md
    purpose: str = Field(max_length=500)  # What this file does
    install_path: str = Field(max_length=200)  # Where to install, e.g., "project root", "~/.claude/commands/"

    created_at: datetime = Field(default_factory=_utc_now)
    download_count: int = Field(default=0)


# Keep Template as alias for backward compatibility during migration
Template = MdStorage


class ConceptStatus(str, Enum):
    """Concept lifecycle status (user-controlled)."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ConceptRunStatus(str, Enum):
    """Concept task execution status."""

    PENDING = "pending"      # Created, waiting for first run
    RUNNING = "running"      # Currently executing
    READY = "ready"          # Has at least one successful snapshot
    FAILED = "failed"        # Last run failed


class Concept(SQLModel, table=True):
    """Concept table for knowledge tracking."""

    __tablename__ = "concepts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, max_length=20)  # Links to User.user_id
    name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    keywords: str = Field(default="")  # JSON array stored as string
    status: str = Field(default=ConceptStatus.ACTIVE)  # Lifecycle status
    run_status: str = Field(default=ConceptRunStatus.PENDING)  # Execution status
    is_public: bool = Field(default=True)  # Whether visible in public listings
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    last_searched_at: Optional[datetime] = Field(default=None)
    search_interval_hours: int = Field(default=24)


class ConceptSnapshot(SQLModel, table=True):
    """Snapshot of concept knowledge at a point in time."""

    __tablename__ = "concept_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    concept_id: int = Field(foreign_key="concepts.id", index=True)
    snapshot_path: str  # Path to JSON file with full graph data
    node_count: int = Field(default=0)
    edge_count: int = Field(default=0)
    sources_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=_utc_now)
    summary: Optional[str] = Field(default=None, max_length=2000)
    md_code: Optional[str] = Field(default=None, max_length=6)  # Code for md-store sharing
