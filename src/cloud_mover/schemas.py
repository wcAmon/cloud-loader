"""Pydantic schemas for API request/response."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RegisterResponse(BaseModel):
    """Response for register endpoint."""

    code: str
    message: str = "註冊成功，請記住您的識別碼"


class UploadResponse(BaseModel):
    """Response for upload endpoint."""

    otp: str
    expires_at: datetime
    message: str = "上傳成功"


class DownloadRequest(BaseModel):
    """Request for download endpoint."""

    code: str
    otp: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str


class StatusResponse(BaseModel):
    """Response for status endpoint."""

    has_backup: bool
    expires_at: Optional[datetime] = None
    file_size: Optional[int] = None
