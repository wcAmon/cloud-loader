"""Backup service for file operations."""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import Session, select

from cloud_mover.config import settings
from cloud_mover.models import ActionLog, Backup, User
from cloud_mover.services.auth import generate_code, generate_otp


def register_user(session: Session, ip: Optional[str] = None) -> User:
    """Register a new user with generated code."""
    # Generate unique code
    while True:
        code = generate_code()
        existing = session.exec(select(User).where(User.code == code)).first()
        if not existing:
            break

    user = User(code=code, created_ip=ip)
    session.add(user)
    session.commit()
    session.refresh(user)

    # Log action
    log = ActionLog(user_id=user.id, action="register", ip=ip)
    session.add(log)
    session.commit()

    return user


def get_user_by_code(session: Session, code: str) -> Optional[User]:
    """Get user by identification code."""
    return session.exec(select(User).where(User.code == code)).first()


def create_backup(
    session: Session,
    user: User,
    file_path: str,
    file_size: int,
    ip: Optional[str] = None,
) -> Backup:
    """Create a new backup record."""
    # Delete any existing backup for this user
    existing = session.exec(
        select(Backup).where(Backup.user_id == user.id)
    ).first()
    if existing:
        # Delete old file
        if os.path.exists(existing.file_path):
            os.remove(existing.file_path)
        session.delete(existing)

    otp = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.otp_expiry_hours)

    backup = Backup(
        user_id=user.id,
        otp=otp,
        file_path=file_path,
        file_size=file_size,
        uploaded_ip=ip,
        expires_at=expires_at,
    )
    session.add(backup)
    session.commit()
    session.refresh(backup)

    # Log action
    log = ActionLog(
        user_id=user.id,
        action="upload",
        ip=ip,
        backup_id=backup.id,
        details=json.dumps({"file_size": file_size}),
    )
    session.add(log)
    session.commit()

    return backup


def get_backup_for_download(
    session: Session, code: str, otp: str
) -> Optional[Backup]:
    """Get backup if code and OTP match and not expired."""
    user = get_user_by_code(session, code)
    if not user:
        return None

    backup = session.exec(
        select(Backup).where(
            Backup.user_id == user.id,
            Backup.otp == otp,
            Backup.expires_at > datetime.now(timezone.utc),
        )
    ).first()

    return backup


def log_download(
    session: Session,
    backup: Backup,
    ip: Optional[str] = None,
) -> None:
    """Log a download action."""
    log = ActionLog(
        user_id=backup.user_id,
        action="download",
        ip=ip,
        backup_id=backup.id,
        details=json.dumps({"source_ip": backup.uploaded_ip}),
    )
    session.add(log)
    session.commit()


def get_backup_status(session: Session, code: str) -> Optional[Backup]:
    """Get current backup status for a user."""
    user = get_user_by_code(session, code)
    if not user:
        return None

    return session.exec(
        select(Backup).where(
            Backup.user_id == user.id,
            Backup.expires_at > datetime.now(timezone.utc),
        )
    ).first()
