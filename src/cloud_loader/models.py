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


class BrainstormEntry(SQLModel, table=True):
    """Daily brainstorm strategy entry from Claude worker."""

    __tablename__ = "brainstorm_entries"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    summary: str = Field(max_length=1000)
    content: str  # Full brainstorm content (markdown)
    concept: str = Field(default="服務agents的網站", max_length=200)
    created_at: datetime = Field(default_factory=_utc_now)


# ---------------------------------------------------------------------------
# Dusk Agent models
# ---------------------------------------------------------------------------


class DuskRunStatus(str, Enum):
    """Dusk agent run status."""

    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"


class DuskRun(SQLModel, table=True):
    """Record of a Dusk agent run."""

    __tablename__ = "dusk_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    summary: str = Field(max_length=2000)
    content: str  # Full markdown content
    status: str = Field(default=DuskRunStatus.SUCCESS)
    duration_seconds: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=_utc_now)


class DuskAskWake(SQLModel, table=True):
    """Questions from Dusk agent to Wake."""

    __tablename__ = "dusk_ask_wake"

    id: Optional[int] = Field(default=None, primary_key=True)
    question: str = Field(max_length=2000)
    context: str = Field(default="", max_length=5000)
    answer: Optional[str] = Field(default=None)
    is_answered: bool = Field(default=False)
    asked_at: datetime = Field(default_factory=_utc_now)
    answered_at: Optional[datetime] = Field(default=None)
    acknowledged_at: Optional[datetime] = Field(default=None)


class DuskConfig(SQLModel, table=True):
    """Dusk worker configuration (singleton row)."""

    __tablename__ = "dusk_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    interval_hours: float = Field(default=6.0)
    enabled: bool = Field(default=False)
    last_run_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=_utc_now)
