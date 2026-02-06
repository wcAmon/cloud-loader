"""Database initialization and session management."""

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine, select

from cloud_loader.config import settings

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Initialize database and create all tables."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)

    # Seed Dusk config if not present
    from cloud_loader.models import DuskConfig

    with Session(engine) as session:
        config = session.exec(select(DuskConfig)).first()
        if not config:
            session.add(DuskConfig(interval_hours=6.0, enabled=False))
            session.commit()


def get_session() -> Generator[Session, None, None]:
    """Yield a database session for dependency injection."""
    with Session(engine) as session:
        yield session
