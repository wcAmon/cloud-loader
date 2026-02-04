"""Authentication router for user registration and API key management."""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlmodel import Session, select

from cloud_loader.database import get_session
from cloud_loader.models import User
from cloud_loader.services.auth import generate_api_key, generate_user_id, is_valid_api_key

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterResponse(BaseModel):
    """Response for registration."""
    api_key: str
    user_id: str
    message: str


class VerifyResponse(BaseModel):
    """Response for API key verification."""
    valid: bool
    user_id: str | None = None


@router.post("/register", response_model=RegisterResponse)
def register(session: Session = Depends(get_session)) -> RegisterResponse:
    """
    Register a new user and receive an API key.

    No input required - creates an anonymous account.
    The API key should be saved to ~/.claude/loader.key for future use.
    """
    # Generate unique user_id and api_key
    user_id = generate_user_id()
    api_key = generate_api_key()

    # Ensure uniqueness (retry if collision)
    while session.exec(select(User).where(User.user_id == user_id)).first():
        user_id = generate_user_id()
    while session.exec(select(User).where(User.api_key == api_key)).first():
        api_key = generate_api_key()

    # Create user
    user = User(user_id=user_id, api_key=api_key)
    session.add(user)
    session.commit()

    return RegisterResponse(
        api_key=api_key,
        user_id=user_id,
        message="Registration successful. Save your API key to ~/.claude/loader.key"
    )


@router.get("/verify", response_model=VerifyResponse)
def verify(
    authorization: str = Header(..., description="Bearer token with API key"),
    session: Session = Depends(get_session)
) -> VerifyResponse:
    """
    Verify an API key is valid.

    Include the API key in the Authorization header:
    Authorization: Bearer ll_xxxxx...
    """
    # Extract API key from Bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    api_key = authorization[7:]  # Remove "Bearer " prefix

    if not is_valid_api_key(api_key):
        return VerifyResponse(valid=False)

    # Look up user
    user = session.exec(select(User).where(User.api_key == api_key)).first()

    if not user:
        return VerifyResponse(valid=False)

    return VerifyResponse(valid=True, user_id=user.user_id)


def get_current_user(
    authorization: str = Header(None, description="Bearer token with API key"),
    session: Session = Depends(get_session)
) -> User | None:
    """
    Dependency to get current user from API key.
    Returns None if no valid API key provided (allows anonymous access).
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    api_key = authorization[7:]

    if not is_valid_api_key(api_key):
        return None

    return session.exec(select(User).where(User.api_key == api_key)).first()


def require_auth(
    authorization: str = Header(..., description="Bearer token with API key"),
    session: Session = Depends(get_session)
) -> User:
    """
    Dependency to require valid API key authentication.
    Raises 401 if not authenticated.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    api_key = authorization[7:]

    if not is_valid_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    user = session.exec(select(User).where(User.api_key == api_key)).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return user
