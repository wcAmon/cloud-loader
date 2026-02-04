"""Loader Tracker API router (authenticated - for agent management)."""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from cloud_loader.database import get_session
from cloud_loader.models import Concept, User, ConceptStatus, ConceptRunStatus
from cloud_loader.routers.auth import require_auth
from cloud_loader.tracker.agents.orchestrator import orchestrator

router = APIRouter(prefix="/api/tracker", tags=["loader-tracker-manage"])


class TopicCreate(BaseModel):
    """Request model for creating a tracked topic."""
    name: str
    description: Optional[str] = None
    keywords: list[str] = []
    search_interval_hours: int = 24
    is_public: bool = True


class TopicUpdate(BaseModel):
    """Request model for updating a tracked topic."""
    name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[list[str]] = None
    status: Optional[str] = None
    search_interval_hours: Optional[int] = None
    is_public: Optional[bool] = None


class TopicResponse(BaseModel):
    """Response model for a tracked topic."""
    id: int
    user_id: str
    name: str
    description: Optional[str]
    keywords: list[str]
    status: str
    run_status: str
    is_public: bool
    created_at: str
    updated_at: str
    last_searched_at: Optional[str]
    search_interval_hours: int


class AgentHint(BaseModel):
    """Hint for agent on what to do next."""
    action: str
    delay_minutes: int
    message: str
    check_endpoint: str


class TopicCreateResponse(BaseModel):
    """Response for topic creation."""
    topic: TopicResponse
    agent_hint: AgentHint


def _to_topic_response(concept: Concept) -> TopicResponse:
    """Convert internal Concept model to TopicResponse."""
    try:
        keywords = json.loads(concept.keywords) if concept.keywords else []
    except json.JSONDecodeError:
        keywords = []

    return TopicResponse(
        id=concept.id,
        user_id=concept.user_id,
        name=concept.name,
        description=concept.description,
        keywords=keywords,
        status=concept.status,
        run_status=concept.run_status,
        is_public=concept.is_public,
        created_at=concept.created_at.isoformat() + "Z",
        updated_at=concept.updated_at.isoformat() + "Z",
        last_searched_at=concept.last_searched_at.isoformat() + "Z" if concept.last_searched_at else None,
        search_interval_hours=concept.search_interval_hours
    )


@router.get("", response_model=list[TopicResponse])
def list_topics(
    user: User = Depends(require_auth),
    session: Session = Depends(get_session)
) -> list[TopicResponse]:
    """List all tracked topics for the authenticated user."""
    topics = session.exec(
        select(Concept).where(Concept.user_id == user.user_id)
    ).all()
    return [_to_topic_response(t) for t in topics]


@router.get("/{topic_id}", response_model=TopicResponse)
def get_topic(
    topic_id: int,
    user: User = Depends(require_auth),
    session: Session = Depends(get_session)
) -> TopicResponse:
    """Get a single tracked topic."""
    topic = session.exec(
        select(Concept).where(
            Concept.id == topic_id,
            Concept.user_id == user.user_id
        )
    ).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    return _to_topic_response(topic)


@router.post("", response_model=TopicCreateResponse, status_code=201)
def create_topic(
    data: TopicCreate,
    user: User = Depends(require_auth),
    session: Session = Depends(get_session)
) -> TopicCreateResponse:
    """Create a new tracked topic. Triggers immediate search in background."""
    topic = Concept(
        user_id=user.user_id,
        name=data.name,
        description=data.description,
        keywords=json.dumps(data.keywords),
        search_interval_hours=data.search_interval_hours,
        is_public=data.is_public,
        run_status=ConceptRunStatus.PENDING
    )
    session.add(topic)
    session.commit()
    session.refresh(topic)

    # Trigger immediate search in background (fire and forget)
    asyncio.create_task(orchestrator.run_concept(topic, session))

    return TopicCreateResponse(
        topic=_to_topic_response(topic),
        agent_hint=AgentHint(
            action="remind_user",
            delay_minutes=15,
            message=f"Loader Tracker is now tracking '{data.name}'. Results will be ready in about 15 minutes.",
            check_endpoint=f"/tracker/{topic.id}/latest"
        )
    )


@router.put("/{topic_id}", response_model=TopicResponse)
def update_topic(
    topic_id: int,
    data: TopicUpdate,
    user: User = Depends(require_auth),
    session: Session = Depends(get_session)
) -> TopicResponse:
    """Update a tracked topic."""
    topic = session.exec(
        select(Concept).where(
            Concept.id == topic_id,
            Concept.user_id == user.user_id
        )
    ).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    if data.name is not None:
        topic.name = data.name
    if data.description is not None:
        topic.description = data.description
    if data.keywords is not None:
        topic.keywords = json.dumps(data.keywords)
    if data.status is not None:
        topic.status = data.status
    if data.search_interval_hours is not None:
        topic.search_interval_hours = data.search_interval_hours
    if data.is_public is not None:
        topic.is_public = data.is_public

    session.add(topic)
    session.commit()
    session.refresh(topic)

    return _to_topic_response(topic)


@router.delete("/{topic_id}", status_code=204)
def delete_topic(
    topic_id: int,
    user: User = Depends(require_auth),
    session: Session = Depends(get_session)
):
    """Delete a tracked topic."""
    topic = session.exec(
        select(Concept).where(
            Concept.id == topic_id,
            Concept.user_id == user.user_id
        )
    ).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    session.delete(topic)
    session.commit()


@router.post("/{topic_id}/run")
async def run_topic_now(
    topic_id: int,
    user: User = Depends(require_auth),
    session: Session = Depends(get_session)
):
    """Manually trigger a topic search."""
    topic = session.exec(
        select(Concept).where(
            Concept.id == topic_id,
            Concept.user_id == user.user_id
        )
    ).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    result = await orchestrator.run_concept(topic, session)
    return result
