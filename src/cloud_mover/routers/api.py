"""API routes for Cloud-Mover."""

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session

from cloud_mover.config import settings
from cloud_mover.database import get_session
from cloud_mover.schemas import (
    DownloadRequest,
    ErrorResponse,
    RegisterResponse,
    StatusResponse,
    UploadResponse,
)
from cloud_mover.services.auth import is_valid_code
from cloud_mover.services.backup import (
    create_backup,
    get_backup_for_download,
    get_backup_status,
    get_user_by_code,
    log_download,
    register_user,
)

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=RegisterResponse)
def register(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
):
    """Register a new user and get an identification code."""
    ip = get_client_ip(request)
    user = register_user(session, ip)
    return RegisterResponse(code=user.code)


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def upload(
    request: Request,
    code: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_session)],
):
    """Upload a backup file."""
    ip = get_client_ip(request)

    # Validate code format
    if not is_valid_code(code):
        raise HTTPException(status_code=400, detail="識別碼格式錯誤")

    # Check user exists
    user = get_user_by_code(session, code)
    if not user:
        raise HTTPException(status_code=404, detail="識別碼不存在，請先註冊")

    # Check file size
    contents = await file.read()
    if len(contents) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"檔案大小超過限制 ({settings.max_file_size_mb}MB)",
        )

    # Save file
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{code}_{uuid.uuid4().hex[:8]}.zip"
    file_path = str(settings.upload_dir / filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    # Create backup record
    backup = create_backup(session, user, file_path, len(contents), ip)

    return UploadResponse(otp=backup.otp, expires_at=backup.expires_at)


@router.post(
    "/download",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def download(
    request: Request,
    body: DownloadRequest,
    session: Annotated[Session, Depends(get_session)],
):
    """Download a backup file."""
    ip = get_client_ip(request)

    # Validate code format
    if not is_valid_code(body.code):
        raise HTTPException(status_code=400, detail="識別碼格式錯誤")

    # Get backup
    backup = get_backup_for_download(session, body.code, body.otp)
    if not backup:
        raise HTTPException(status_code=404, detail="OTP 錯誤或已過期")

    # Check file exists
    if not os.path.exists(backup.file_path):
        raise HTTPException(status_code=404, detail="備份檔案不存在")

    # Log download
    log_download(session, backup, ip)

    return FileResponse(
        backup.file_path,
        media_type="application/zip",
        filename=f"claude-backup-{body.code}.zip",
    )


@router.get(
    "/status/{code}",
    response_model=StatusResponse,
    responses={400: {"model": ErrorResponse}},
)
def status(
    code: str,
    session: Annotated[Session, Depends(get_session)],
):
    """Check backup status for a user."""
    if not is_valid_code(code):
        raise HTTPException(status_code=400, detail="識別碼格式錯誤")

    backup = get_backup_status(session, code)
    if not backup:
        return StatusResponse(has_backup=False)

    return StatusResponse(
        has_backup=True,
        expires_at=backup.expires_at,
        file_size=backup.file_size,
    )
