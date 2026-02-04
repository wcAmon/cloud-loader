"""MD Storage service - publicly accessible, no expiration."""

from typing import Optional

from sqlmodel import Session, func, select

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
    """Create a new MD storage record. Files are permanent and public."""
    for _ in range(MAX_CODE_GENERATION_ATTEMPTS):
        code = generate_code()
        stmt = select(MdStorage).where(MdStorage.code == code)
        existing = session.exec(stmt).first()
        if not existing:
            break
    else:
        raise RuntimeError("Failed to generate unique code after max attempts")

    md_storage = MdStorage(
        code=code,
        content=content,
        content_size=len(content.encode("utf-8")),
        filename=filename,
        purpose=purpose,
        install_path=install_path,
    )
    session.add(md_storage)
    session.commit()
    session.refresh(md_storage)

    return md_storage


def get_md_storage_by_code(session: Session, code: str) -> Optional[MdStorage]:
    """Get MD storage by code. No expiration - files are permanent."""
    stmt = select(MdStorage).where(MdStorage.code == code)
    return session.exec(stmt).first()


def list_md_storage(
    session: Session,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[MdStorage], int]:
    """List all MD files with pagination. Returns (files, total_count)."""
    count_stmt = select(func.count()).select_from(MdStorage)
    total = session.exec(count_stmt).one()

    stmt = (
        select(MdStorage)
        .order_by(MdStorage.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    files = list(session.exec(stmt).all())

    return files, total


def increment_download_count(session: Session, md_storage: MdStorage) -> None:
    """Increment the download count."""
    md_storage.download_count += 1
    session.add(md_storage)
    session.commit()


# Backward compatibility aliases
create_template = create_md_storage
get_template_by_code = get_md_storage_by_code
