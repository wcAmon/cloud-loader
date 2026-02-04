"""Cleanup service for expired backups only. MD files are permanent."""

import os
from datetime import datetime, timezone

from sqlmodel import Session, select

from cloud_loader.models import Backup


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


# Note: MD Storage files are permanent and publicly accessible - no cleanup needed
