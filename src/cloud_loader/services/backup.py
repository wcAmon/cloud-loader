"""Backup service for file operations."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import Session, select

from cloud_loader.config import settings
from cloud_loader.models import Backup
from cloud_loader.services.auth import generate_code

MAX_CODE_GENERATION_ATTEMPTS = 100


def create_backup(
    session: Session,
    file_path: str,
    file_size: int,
) -> Backup:
    """Create a new backup record with unique code."""
    # Generate unique code
    for _ in range(MAX_CODE_GENERATION_ATTEMPTS):
        code = generate_code()
        existing = session.exec(select(Backup).where(Backup.code == code)).first()
        if not existing:
            break
    else:
        raise RuntimeError("Failed to generate unique code after max attempts")

    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.expiry_hours)

    backup = Backup(
        code=code,
        file_path=file_path,
        file_size=file_size,
        expires_at=expires_at,
    )
    session.add(backup)
    session.commit()
    session.refresh(backup)

    return backup


def get_backup_by_code(session: Session, code: str) -> Optional[Backup]:
    """Get backup by code if not expired."""
    return session.exec(
        select(Backup).where(
            Backup.code == code,
            Backup.expires_at > datetime.now(timezone.utc),
        )
    ).first()
