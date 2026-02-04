"""MD Storage service for storing and sharing MD files."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import Session, select

from cloud_loader.config import settings
from cloud_loader.models import MdStorage
from cloud_loader.services.auth import generate_code

MAX_CODE_GENERATION_ATTEMPTS = 100


def create_md_storage(
    session: Session,
    content: str,
    filename: str,
    purpose: str,
    install_path: str,
) -> MdStorage:
    """Create a new MD storage record with unique code."""
    for _ in range(MAX_CODE_GENERATION_ATTEMPTS):
        code = generate_code()
        stmt = select(MdStorage).where(MdStorage.code == code)
        existing = session.exec(stmt).first()
        if not existing:
            break
    else:
        raise RuntimeError("Failed to generate unique code after max attempts")

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.template_expiry_days
    )

    md_storage = MdStorage(
        code=code,
        content=content,
        content_size=len(content.encode("utf-8")),
        filename=filename,
        purpose=purpose,
        install_path=install_path,
        expires_at=expires_at,
    )
    session.add(md_storage)
    session.commit()
    session.refresh(md_storage)

    return md_storage


def get_md_storage_by_code(session: Session, code: str) -> Optional[MdStorage]:
    """Get MD storage by code if not expired."""
    stmt = select(MdStorage).where(
        MdStorage.code == code,
        MdStorage.expires_at > datetime.now(timezone.utc),
    )
    return session.exec(stmt).first()


def increment_download_count(session: Session, md_storage: MdStorage) -> None:
    """Increment the download count."""
    md_storage.download_count += 1
    session.add(md_storage)
    session.commit()


# Backward compatibility aliases
create_template = create_md_storage
get_template_by_code = get_md_storage_by_code
