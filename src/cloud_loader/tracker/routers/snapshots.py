"""Snapshots API router."""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from cloud_loader.database import get_session
from cloud_loader.models import Concept, User
from cloud_loader.routers.auth import require_auth
from cloud_loader.tracker.services.snapshot_store import get_snapshot, list_snapshots

router = APIRouter(prefix="/api/tracker/{topic_id}/snapshots", tags=["loader-tracker-snapshots"])


@router.get("")
async def list_topic_snapshots(
    topic_id: int,
    user: User = Depends(require_auth),
    session: Session = Depends(get_session)
):
    """List all snapshots for a tracked topic."""
    statement = select(Concept).where(
        Concept.id == topic_id,
        Concept.user_id == user.user_id
    )
    topic = session.exec(statement).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    return await list_snapshots(topic_id)


@router.get("/{timestamp}")
async def get_topic_snapshot(
    topic_id: int,
    timestamp: str,
    user: User = Depends(require_auth),
    session: Session = Depends(get_session)
):
    """Get a specific snapshot. Use 'latest' for most recent."""
    statement = select(Concept).where(
        Concept.id == topic_id,
        Concept.user_id == user.user_id
    )
    topic = session.exec(statement).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Remove .json extension if provided
    if timestamp.endswith(".json"):
        timestamp = timestamp[:-5]

    snapshot = await get_snapshot(topic_id, timestamp)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return JSONResponse(content=snapshot)
