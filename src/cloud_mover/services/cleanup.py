"""Cleanup service for expired backups."""

import os
from datetime import datetime, timezone

from sqlmodel import Session, select

from cloud_mover.models import Backup


def cleanup_expired_backups(session: Session) -> int:
    """Delete expired backups and their files. Returns count of deleted items."""
    now = datetime.now(timezone.utc)

    expired = session.exec(select(Backup).where(Backup.expires_at < now)).all()

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
