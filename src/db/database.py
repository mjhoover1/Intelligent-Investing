"""SQLAlchemy database configuration and session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings

settings = get_settings()

# Create engine with SQLite-specific settings
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=False,  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Allow accessing attributes after commit/close
)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Usage:
        with get_db() as db:
            db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    from .models import Base

    Base.metadata.create_all(bind=engine)
