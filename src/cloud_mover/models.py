"""Database models using SQLModel."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """User table for storing identification codes."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=6)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_ip: Optional[str] = Field(default=None, max_length=45)


class Backup(SQLModel, table=True):
    """Backup table for storing upload metadata."""

    __tablename__ = "backups"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    otp: str = Field(max_length=4)
    file_path: str
    file_size: Optional[int] = Field(default=None)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    uploaded_ip: Optional[str] = Field(default=None, max_length=45)
    expires_at: datetime


class ActionLog(SQLModel, table=True):
    """Action log table for tracking all operations."""

    __tablename__ = "action_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    action: str = Field(max_length=20)  # register, upload, download, cleanup
    ip: Optional[str] = Field(default=None, max_length=45)
    backup_id: Optional[int] = Field(default=None, foreign_key="backups.id")
    details: Optional[str] = Field(default=None)  # JSON string
    created_at: datetime = Field(default_factory=datetime.utcnow)
