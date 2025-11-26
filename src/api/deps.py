"""FastAPI dependencies."""

from __future__ import annotations

from typing import Any, Generator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from src.db.database import get_db as db_context
from src.db.models import User
from src.config import get_settings

settings = get_settings()


def get_db() -> Generator[Session, None, None]:
    """Yield a database session."""
    with db_context() as db:
        yield db


def get_current_user(db: Session = Depends(get_db)) -> Any:
    """Get or create the default user.

    For MVP, we use a single default user.
    Returns a SQLAlchemy User model (typed as Any to avoid FastAPI validation issues).
    """
    user = db.query(User).filter_by(email=settings.default_user_email).first()
    if not user:
        user = User(email=settings.default_user_email)
        db.add(user)
        db.flush()
    return user


def require_api_key(x_api_key: str = Header(None)) -> None:
    """Validate API key if configured.

    If no API key is configured in settings, all requests are allowed.
    Otherwise, the X-API-Key header must match.
    """
    if not settings.api_key:
        # No API key configured, allow all requests
        return

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
