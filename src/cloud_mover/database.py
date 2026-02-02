"""Database initialization and session management."""

from sqlmodel import Session, SQLModel, create_engine

from cloud_mover.config import settings

# Ensure data directory exists
settings.data_dir.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Initialize database and create all tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Yield a database session for dependency injection."""
    with Session(engine) as session:
        yield session
