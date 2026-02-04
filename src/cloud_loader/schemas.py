"""Pydantic schemas for API request/response."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response for upload endpoint."""

    code: str = Field(min_length=6, max_length=6)
    expires_at: datetime
    message: str = "Upload successful, please remember your verification code"


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str


# MD Storage schemas


class MdMetadata(BaseModel):
    """Metadata about the MD file."""

    filename: str = Field(
        min_length=1,
        max_length=100,
        description="Filename, e.g., CLAUDE.md, DEVELOPMENT.md, my-skill.md",
    )
    purpose: str = Field(
        min_length=1,
        max_length=500,
        description="What this file does, e.g., 'Project instructions for Claude Code'",
    )
    install_path: str = Field(
        min_length=1,
        max_length=200,
        description="Where to install, e.g., 'project root', '~/.claude/commands/'",
    )


class MdStorageCreateRequest(BaseModel):
    """Request for storing an MD file."""

    content: str = Field(min_length=1, description="MD file content")
    metadata: MdMetadata = Field(description="Information about the MD file")


class MdStorageCreateResponse(BaseModel):
    """Response for MD storage creation."""

    code: str = Field(min_length=6, max_length=6)
    expires_at: datetime
    message: str = "MD file stored successfully"


class MdStorageGetResponse(BaseModel):
    """Response for getting a stored MD file."""

    code: str
    content: str
    content_size: int
    metadata: MdMetadata
    created_at: datetime
    expires_at: datetime
    download_count: int


# Backward compatibility aliases
TemplateCreateRequest = MdStorageCreateRequest
TemplateCreateResponse = MdStorageCreateResponse
TemplateGetResponse = MdStorageGetResponse
