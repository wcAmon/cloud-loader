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


class TemplateType(str, Enum):
    """Template type enum."""

    CLAUDE_MD = "CLAUDE.md"
    AGENTS_MD = "AGENTS.md"


class Template(SQLModel, table=True):
    """Template table for storing shared templates."""

    __tablename__ = "templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=6)
    template_type: str = Field(default=TemplateType.CLAUDE_MD)
    title: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    content: str
    content_size: int
    created_at: datetime = Field(default_factory=_utc_now)
    expires_at: datetime
    download_count: int = Field(default=0)
