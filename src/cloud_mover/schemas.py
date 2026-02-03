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


# Template schemas


class TemplateCreateRequest(BaseModel):
    """Request for creating a template."""

    template_type: str = Field(
        default="CLAUDE.md",
        pattern="^(CLAUDE\\.md|AGENTS\\.md)$",
        description="Template type: CLAUDE.md or AGENTS.md",
    )
    title: str = Field(min_length=1, max_length=100, description="Template title")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Optional description"
    )
    content: str = Field(min_length=1, description="Template content (Markdown)")


class TemplateCreateResponse(BaseModel):
    """Response for template creation."""

    code: str = Field(min_length=6, max_length=6)
    expires_at: datetime
    message: str = "Template shared successfully"


class TemplateGetResponse(BaseModel):
    """Response for getting a template."""

    code: str
    template_type: str
    title: str
    description: Optional[str]
    content: str
    content_size: int
    created_at: datetime
    expires_at: datetime
    download_count: int
