"""API routes for Cloud-Loader."""

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from sqlmodel import Session

from cloud_loader.config import settings
from cloud_loader.database import get_session
from cloud_loader.schemas import (
    ErrorResponse,
    MdMetadata,
    MdStorageCreateRequest,
    MdStorageCreateResponse,
    MdStorageGetResponse,
    MdStorageListItem,
    MdStorageListResponse,
    UploadResponse,
)
from cloud_loader.services.auth import is_valid_code
from cloud_loader.services.backup import create_backup, get_backup_by_code
from cloud_loader.services.template import (
    create_md_storage,
    get_md_storage_by_code,
    increment_download_count,
    list_md_storage,
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


# MD Storage endpoints


@router.post(
    "/md",
    response_model=MdStorageCreateResponse,
    responses={400: {"model": ErrorResponse}},
)
def store_md(
    request: MdStorageCreateRequest,
    session: Annotated[Session, Depends(get_session)],
):
    """Store an MD file and get a verification code."""
    content_size = len(request.content.encode("utf-8"))

    if content_size > settings.max_template_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"MD file too large: {content_size} bytes "
            f"(limit: {settings.max_template_size_kb}KB). "
            f"Consider removing verbose comments or splitting into multiple files.",
        )

    md_storage = create_md_storage(
        session=session,
        content=request.content,
        filename=request.metadata.filename,
        purpose=request.metadata.purpose,
        install_path=request.metadata.install_path,
    )

    return MdStorageCreateResponse(code=md_storage.code)


@router.get(
    "/md",
    response_model=MdStorageListResponse,
)
def list_md(
    session: Annotated[Session, Depends(get_session)],
    limit: int = 50,
    offset: int = 0,
):
    """List all stored MD files. Files are public and permanent."""
    files, total = list_md_storage(session, limit=min(limit, 100), offset=offset)

    return MdStorageListResponse(
        files=[
            MdStorageListItem(
                code=f.code,
                filename=f.filename,
                purpose=f.purpose,
                content_size=f.content_size,
                created_at=f.created_at,
                download_count=f.download_count,
            )
            for f in files
        ],
        total=total,
    )


@router.get(
    "/md/{code}",
    response_model=MdStorageGetResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_md(
    code: str,
    session: Annotated[Session, Depends(get_session)],
):
    """Get MD file metadata and content by code."""
    if not is_valid_code(code):
        raise HTTPException(status_code=400, detail="Invalid code format")

    md_storage = get_md_storage_by_code(session, code)
    if not md_storage:
        raise HTTPException(status_code=404, detail="MD file not found")

    increment_download_count(session, md_storage)

    return MdStorageGetResponse(
        code=md_storage.code,
        content=md_storage.content,
        content_size=md_storage.content_size,
        metadata=MdMetadata(
            filename=md_storage.filename,
            purpose=md_storage.purpose,
            install_path=md_storage.install_path,
        ),
        created_at=md_storage.created_at,
        download_count=md_storage.download_count,
    )


@router.get(
    "/md/{code}/raw",
    response_class=PlainTextResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_md_raw(
    code: str,
    session: Annotated[Session, Depends(get_session)],
):
    """Get raw MD content as plain text (for direct download)."""
    if not is_valid_code(code):
        raise HTTPException(status_code=400, detail="Invalid code format")

    md_storage = get_md_storage_by_code(session, code)
    if not md_storage:
        raise HTTPException(status_code=404, detail="MD file not found")

    increment_download_count(session, md_storage)

    return PlainTextResponse(
        content=md_storage.content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{md_storage.filename}"'
        },
    )


# Skill download endpoint

LOADER_LAND_SKILL = '''---
name: loader-land
description: Use when user mentions "loader.land", "cloud migration", "transfer settings", "store MD file", "share markdown", "import md code", "track topics", or needs to backup/restore AI assistant configurations.
---

# Loader.land - AI Agent Services

## Services Overview

| Service | Auth Required | Description |
|---------|---------------|-------------|
| Migration | No | Transfer settings (24h, password protected) |
| MD Storage | No | Store/share any markdown (permanent, public) |
| Loader Tracker | Yes (API key) | Track topics, build knowledge graphs |

## 1. Migration (Settings Transfer) - No API key
```bash
# Upload (returns 6-char code, valid 24h)
curl -X POST https://loader.land/upload -F "file=@backup.zip"

# Download
curl -o backup.zip https://loader.land/download/[CODE]
```

## 2. MD Storage - No API key, Permanent & Public
Store any markdown file with metadata. Files are permanent and publicly browsable.

```bash
# List all stored files
curl https://loader.land/md

# Store MD file (returns 6-char code)
curl -X POST https://loader.land/md \\
  -H "Content-Type: application/json" \\
  -d '{
    "content": "# My content...",
    "metadata": {
      "filename": "my-skill.md",
      "purpose": "Custom skill for data analysis",
      "install_path": "~/.claude/commands/"
    }
  }'

# Get file info
curl https://loader.land/md/[CODE]

# Get raw content
curl https://loader.land/md/[CODE]/raw -o my-skill.md
```

## 3. Loader Tracker - Requires API key

### Register (only needed for Loader Tracker)
```bash
API_RESPONSE=$(curl -s -X POST https://loader.land/api/auth/register)
API_KEY=$(echo "$API_RESPONSE" | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)
echo "$API_KEY" > ~/.claude/loader.key
chmod 600 ~/.claude/loader.key
```

### Create tracked topic
```bash
API_KEY=$(cat ~/.claude/loader.key)

curl -X POST https://loader.land/api/tracker \\
  -H "Authorization: Bearer $API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "AI Agents", "keywords": ["AI", "agents", "LLM"]}'
```

### Browse public topics (no auth needed)
```bash
curl https://loader.land/tracker
curl https://loader.land/tracker/{id}/latest
```
'''


@router.get(
    "/skills/loader-land-skill",
    response_class=PlainTextResponse,
)
def get_loader_land_skill():
    """Download the loader-land skill for AI assistants.

    Install locations by tool:
    - Claude Code: ~/.claude/commands/loader-land.md
    - Codex: ~/.codex/skills/loader-land.md
    - OpenClaw: ~/.openclaw/skills/loader-land.md
    """
    return PlainTextResponse(
        content=LOADER_LAND_SKILL,
        media_type="text/markdown",
        headers={
            "Content-Disposition": 'attachment; filename="loader-land.md"'
        },
    )
