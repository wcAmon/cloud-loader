"""API routes for Cloud-Mover."""

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from sqlmodel import Session

from cloud_mover.config import settings
from cloud_mover.database import get_session
from cloud_mover.schemas import (
    ErrorResponse,
    TemplateCreateRequest,
    TemplateCreateResponse,
    TemplateGetResponse,
    UploadResponse,
)
from cloud_mover.services.auth import is_valid_code
from cloud_mover.services.backup import create_backup, get_backup_by_code
from cloud_mover.services.template import (
    create_template,
    get_template_by_code,
    increment_download_count,
)

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


# Template sharing endpoints


@router.post(
    "/templates",
    response_model=TemplateCreateResponse,
    responses={400: {"model": ErrorResponse}},
)
def share_template(
    request: TemplateCreateRequest,
    session: Annotated[Session, Depends(get_session)],
):
    """Share a CLAUDE.md or AGENTS.md template and get a verification code."""
    content_size = len(request.content.encode("utf-8"))

    if content_size > settings.max_template_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Template too large: {content_size} bytes "
            f"(limit: {settings.max_template_size_kb}KB). "
            f"Consider removing verbose comments or splitting into multiple files.",
        )

    template = create_template(
        session=session,
        template_type=request.template_type,
        title=request.title,
        content=request.content,
        description=request.description,
    )

    return TemplateCreateResponse(code=template.code, expires_at=template.expires_at)


@router.get(
    "/templates/{code}",
    response_model=TemplateGetResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_template(
    code: str,
    session: Annotated[Session, Depends(get_session)],
):
    """Get template metadata and content by verification code."""
    if not is_valid_code(code):
        raise HTTPException(status_code=400, detail="Invalid verification code format")

    template = get_template_by_code(session, code)
    if not template:
        raise HTTPException(
            status_code=404, detail="Template not found or expired"
        )

    increment_download_count(session, template)

    return TemplateGetResponse(
        code=template.code,
        template_type=template.template_type,
        title=template.title,
        description=template.description,
        content=template.content,
        content_size=template.content_size,
        created_at=template.created_at,
        expires_at=template.expires_at,
        download_count=template.download_count,
    )


@router.get(
    "/templates/{code}/raw",
    response_class=PlainTextResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_template_raw(
    code: str,
    session: Annotated[Session, Depends(get_session)],
):
    """Get raw template content as plain text (for direct download)."""
    if not is_valid_code(code):
        raise HTTPException(status_code=400, detail="Invalid verification code format")

    template = get_template_by_code(session, code)
    if not template:
        raise HTTPException(
            status_code=404, detail="Template not found or expired"
        )

    increment_download_count(session, template)

    return PlainTextResponse(
        content=template.content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{template.template_type}"'
        },
    )
