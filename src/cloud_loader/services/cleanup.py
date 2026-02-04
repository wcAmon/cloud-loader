"""Cleanup service for expired backups and MD storage."""

import os
from datetime import datetime, timezone

from sqlmodel import Session, select

from cloud_loader.models import Backup, MdStorage


def cleanup_expired_backups(session: Session) -> int:
    """Delete expired backups and their files. Returns count of deleted items."""
    now = datetime.now(timezone.utc)

    stmt = select(Backup).where(Backup.expires_at < now)
    expired = session.exec(stmt).all()

    count = 0
    for backup in expired:
        if os.path.exists(backup.file_path):
            try:
                os.remove(backup.file_path)
            except OSError:
                pass
        session.delete(backup)
        count += 1

    if count > 0:
        session.commit()

    return count


def cleanup_expired_templates(session: Session) -> int:
    """Delete expired MD storage entries. Returns count of deleted items."""
    now = datetime.now(timezone.utc)

    stmt = select(MdStorage).where(MdStorage.expires_at < now)
    expired = session.exec(stmt).all()

    count = 0
    for md_storage in expired:
        session.delete(md_storage)
        count += 1

    if count > 0:
        session.commit()

    return count
