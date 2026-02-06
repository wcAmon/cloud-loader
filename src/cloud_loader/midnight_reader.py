"""Read-only access to Midnight's database for the unified Hub page."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

MIDNIGHT_DB = Path("/home/wake/midnight/data/midnight.db")
MIDNIGHT_MEMORY = Path("/home/wake/MIDNIGHT-MEMORY.md")

midnight_engine = create_engine(
    f"sqlite:///{MIDNIGHT_DB}",
    echo=False,
    connect_args={"check_same_thread": False},
)


# Mirror midnight's models (read-only, no migrations)
class MidnightRun(SQLModel, table=False):
    """Mirror of midnight's AgentRun table."""
    __tablename__ = "agent_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    summary: str = Field(max_length=2000)
    content: str
    status: str
    duration_seconds: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MidnightAskWake(SQLModel, table=False):
    """Mirror of midnight's AskWakeEntry table."""
    __tablename__ = "ask_wake"

    id: Optional[int] = Field(default=None, primary_key=True)
    question: str = Field(max_length=2000)
    context: str = Field(default="")
    answer: Optional[str] = None
    is_answered: bool = False
    asked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    answered_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None


class MidnightConfig(SQLModel, table=False):
    """Mirror of midnight's WorkerConfig table."""
    __tablename__ = "worker_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    interval_hours: float = 12.0
    enabled: bool = True
    last_run_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def get_midnight_runs(limit: int = 5) -> list[dict]:
    """Get recent midnight agent runs."""
    from sqlalchemy import text
    with Session(midnight_engine) as session:
        result = session.execute(
            text("SELECT id, title, summary, content, status, duration_seconds, created_at FROM agent_runs ORDER BY created_at DESC LIMIT :limit"),
            {"limit": limit},
        )
        return [dict(row._mapping) for row in result]


def get_midnight_ask_wake() -> list[dict]:
    """Get midnight Ask Wake entries."""
    from sqlalchemy import text
    with Session(midnight_engine) as session:
        result = session.execute(
            text("SELECT id, question, context, answer, is_answered, asked_at, answered_at FROM ask_wake ORDER BY asked_at DESC"),
        )
        return [dict(row._mapping) for row in result]


def answer_midnight_question(entry_id: int, answer: str) -> bool:
    """Answer a midnight agent question."""
    from sqlalchemy import text
    with Session(midnight_engine) as session:
        session.execute(
            text("UPDATE ask_wake SET answer = :answer, is_answered = 1, answered_at = :now WHERE id = :id"),
            {"answer": answer, "id": entry_id, "now": datetime.now(timezone.utc).isoformat()},
        )
        session.commit()
        return True


def get_midnight_config() -> dict | None:
    """Get midnight worker config."""
    from sqlalchemy import text
    with Session(midnight_engine) as session:
        result = session.execute(text("SELECT * FROM worker_config LIMIT 1"))
        row = result.first()
        return dict(row._mapping) if row else None


def get_midnight_memory_updated() -> datetime | None:
    """Get midnight memory file last modified time."""
    if MIDNIGHT_MEMORY.exists():
        mtime = MIDNIGHT_MEMORY.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc)
    return None
