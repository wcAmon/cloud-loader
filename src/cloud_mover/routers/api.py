"""API routes for Cloud-Mover."""

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session

from cloud_mover.config import settings
from cloud_mover.database import get_session
from cloud_mover.schemas import ErrorResponse, UploadResponse
from cloud_mover.services.auth import is_valid_code
from cloud_mover.services.backup import create_backup, get_backup_by_code

router = APIRouter()


def _format_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={400: {"model": ErrorResponse}},
)
async def upload(
    file: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_session)],
):
    """Upload a backup file and get a verification code."""
    contents = await file.read()
    file_size = len(contents)

    if file_size > settings.max_file_size_bytes:
        actual_size = _format_size(file_size)
        max_size = f"{settings.max_file_size_mb}MB"
        excess = _format_size(file_size - settings.max_file_size_bytes)

        raise HTTPException(
            status_code=400,
            detail=(
                f"File too large: {actual_size} (limit: {max_size}, excess: {excess}). "
                f"Please reduce size by excluding: "
                f"(1) node_modules directories, "
                f"(2) AI models or large binaries, "
                f"(3) cache files, "
                f"(4) items that can be reinstalled. "
                f"Use 'du -sh ~/.claude/*/' to identify large folders."
            ),
        )

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.zip"
    file_path = str(settings.upload_dir / filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    backup = create_backup(session, file_path, file_size)

    return UploadResponse(code=backup.code, expires_at=backup.expires_at)


@router.get(
    "/download/{code}",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def download(
    code: str,
    session: Annotated[Session, Depends(get_session)],
):
    """Download a backup file using verification code."""
    if not is_valid_code(code):
        raise HTTPException(status_code=400, detail="Invalid verification code format")

    backup = get_backup_by_code(session, code)
    if not backup:
        raise HTTPException(status_code=404, detail="Verification code not found or expired")

    if not os.path.exists(backup.file_path):
        raise HTTPException(status_code=404, detail="Backup file not found")

    return FileResponse(
        backup.file_path,
        media_type="application/zip",
        filename=f"claude-backup-{code}.zip",
    )
