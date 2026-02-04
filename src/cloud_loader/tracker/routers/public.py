"""Loader Tracker public API (no authentication required)."""

import base64
import json
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from cloud_loader.database import get_session
from cloud_loader.models import Concept, ConceptSnapshot
from cloud_loader.tracker.services.snapshot_store import get_snapshot

router = APIRouter(prefix="/tracker", tags=["loader-tracker"])


class PublicTopicResponse(BaseModel):
    """Public view of a tracked topic."""

    id: int
    name: str
    description: Optional[str]
    keywords: list[str]
    status: str
    run_status: str
    node_count: int
    edge_count: int
    sources_count: int
    created_at: str
    updated_at: str
    last_searched_at: Optional[str]


class TopicListResponse(BaseModel):
    """Paginated list of tracked topics."""

    topics: list[PublicTopicResponse]
    next_cursor: Optional[str]
    has_more: bool


def _encode_cursor(topic_id: int, updated_at: str) -> str:
    """Encode cursor for pagination."""
    data = f"{topic_id}:{updated_at}"
    return base64.urlsafe_b64encode(data.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[int, str]:
    """Decode cursor to (topic_id, updated_at)."""
    try:
        data = base64.urlsafe_b64decode(cursor.encode()).decode()
        topic_id, updated_at = data.split(":", 1)
        return int(topic_id), updated_at
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid cursor format")


def _to_public_topic(concept: Concept, snapshot: Optional[ConceptSnapshot] = None) -> PublicTopicResponse:
    """Convert internal Concept to public TopicResponse."""
    try:
        keywords = json.loads(concept.keywords) if concept.keywords else []
    except json.JSONDecodeError:
        keywords = []

    return PublicTopicResponse(
        id=concept.id,
        name=concept.name,
        description=concept.description,
        keywords=keywords,
        status=concept.status,
        run_status=concept.run_status,
        node_count=snapshot.node_count if snapshot else 0,
        edge_count=snapshot.edge_count if snapshot else 0,
        sources_count=snapshot.sources_count if snapshot else 0,
        created_at=concept.created_at.isoformat() + "Z",
        updated_at=concept.updated_at.isoformat() + "Z",
        last_searched_at=concept.last_searched_at.isoformat() + "Z" if concept.last_searched_at else None,
    )


@router.get("", response_model=TopicListResponse)
def list_public_topics(
    session: Annotated[Session, Depends(get_session)],
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None, description="Search by name or keywords"),
):
    """List all public tracked topics with cursor-based pagination."""
    # Base query: only public and active topics
    query = select(Concept).where(
        Concept.is_public == True,
        Concept.status == "active"
    )

    # Apply keyword filter
    if keyword:
        query = query.where(
            (Concept.name.contains(keyword)) | (Concept.keywords.contains(keyword))
        )

    # Apply cursor (pagination)
    if cursor:
        cursor_id, cursor_updated = _decode_cursor(cursor)
        # Get topics updated before the cursor position
        query = query.where(
            (Concept.updated_at < cursor_updated) |
            ((Concept.updated_at == cursor_updated) & (Concept.id < cursor_id))
        )

    # Order by updated_at desc, then id desc for consistent ordering
    query = query.order_by(Concept.updated_at.desc(), Concept.id.desc())

    # Fetch one extra to check if there's more
    topics = session.exec(query.limit(limit + 1)).all()

    has_more = len(topics) > limit
    topics = topics[:limit]

    # Get latest snapshot for each topic
    results = []
    for topic in topics:
        snapshot = session.exec(
            select(ConceptSnapshot)
            .where(ConceptSnapshot.concept_id == topic.id)
            .order_by(ConceptSnapshot.created_at.desc())
            .limit(1)
        ).first()
        results.append(_to_public_topic(topic, snapshot))

    # Generate next cursor
    next_cursor = None
    if has_more and topics:
        last = topics[-1]
        next_cursor = _encode_cursor(last.id, last.updated_at.isoformat())

    return TopicListResponse(
        topics=results,
        next_cursor=next_cursor,
        has_more=has_more
    )


@router.get("/{topic_id}", response_model=PublicTopicResponse)
def get_public_topic(
    topic_id: int,
    session: Annotated[Session, Depends(get_session)],
):
    """Get a single public tracked topic by ID."""
    topic = session.exec(
        select(Concept).where(
            Concept.id == topic_id,
            Concept.is_public == True
        )
    ).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    snapshot = session.exec(
        select(ConceptSnapshot)
        .where(ConceptSnapshot.concept_id == topic.id)
        .order_by(ConceptSnapshot.created_at.desc())
        .limit(1)
    ).first()

    return _to_public_topic(topic, snapshot)


@router.get("/{topic_id}/latest")
async def get_public_topic_latest(
    topic_id: int,
    session: Annotated[Session, Depends(get_session)],
):
    """Get the latest snapshot for a public tracked topic."""
    topic = session.exec(
        select(Concept).where(
            Concept.id == topic_id,
            Concept.is_public == True
        )
    ).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    snapshot = await get_snapshot(topic_id, "latest")
    if not snapshot:
        raise HTTPException(status_code=404, detail="No snapshot available yet")

    return JSONResponse(content=snapshot)
