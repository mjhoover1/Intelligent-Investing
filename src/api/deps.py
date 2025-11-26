"""FastAPI dependencies."""

from __future__ import annotations

from typing import Any, Generator, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.db.database import get_db as db_context
from src.db.models import User, UserApiKey
from src.config import get_settings
from src.core.auth.security import decode_access_token, verify_api_key

settings = get_settings()

# OAuth2 scheme for JWT tokens (used in Swagger UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

# HTTP Bearer for JWT tokens
http_bearer = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session."""
    with db_context() as db:
        yield db


def _get_user_from_jwt(token: str, db: Session) -> Optional[User]:
    """Decode JWT token and return user."""
    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if user and user.is_active:
        return user
    return None


def _get_user_from_api_key(api_key: str, db: Session) -> Optional[User]:
    """Validate API key and return user."""
    from datetime import datetime

    # Get all active API keys
    api_keys = db.query(UserApiKey).filter(
        UserApiKey.is_active == True  # noqa: E712
    ).all()

    for key in api_keys:
        # Check expiration
        if key.expires_at and key.expires_at < datetime.utcnow():
            continue

        # Verify the key
        if verify_api_key(api_key, key.key_hash):
            # Update last used
            key.last_used_at = datetime.utcnow()
            db.commit()

            # Return the user
            user = db.query(User).filter(User.id == key.user_id).first()
            if user and user.is_active:
                return user

    return None


def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    x_api_key: Optional[str] = Header(None),
) -> User:
    """Get the current authenticated user.

    Supports multiple authentication methods:
    1. JWT Bearer token (Authorization: Bearer <token>)
    2. Per-user API key (X-API-Key header)
    3. Fallback to default user if no auth and no global API key configured

    Returns:
        Authenticated User model
    """
    user = None

    # Try JWT token from oauth2 scheme first
    if token:
        user = _get_user_from_jwt(token, db)

    # Try Bearer token header
    if not user and bearer:
        user = _get_user_from_jwt(bearer.credentials, db)

    # Try per-user API key
    if not user and x_api_key:
        user = _get_user_from_api_key(x_api_key, db)

    # If authenticated, return the user
    if user:
        return user

    # Fallback: If no global API key is configured, use default user (backward compatibility)
    if not settings.api_key:
        default_user = db.query(User).filter_by(email=settings.default_user_email).first()
        if not default_user:
            default_user = User(email=settings.default_user_email, is_active=True)
            db.add(default_user)
            db.flush()
        return default_user

    # If global API key is set but doesn't match, require authentication
    if x_api_key == settings.api_key:
        # Global API key matches - use default user
        default_user = db.query(User).filter_by(email=settings.default_user_email).first()
        if not default_user:
            default_user = User(email=settings.default_user_email, is_active=True)
            db.add(default_user)
            db.flush()
        return default_user

    # No valid authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_api_key(
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> None:
    """Validate authentication for protected endpoints.

    Accepts:
    1. JWT Bearer token
    2. Per-user API key
    3. Global API key (legacy)
    """
    # If no global API key configured and no auth provided, allow (dev mode)
    if not settings.api_key and not x_api_key and not bearer:
        return

    # Check JWT Bearer token
    if bearer:
        payload = decode_access_token(bearer.credentials)
        if payload and payload.get("sub"):
            return  # Valid JWT

    # Check per-user API key
    if x_api_key:
        user = _get_user_from_api_key(x_api_key, db)
        if user:
            return  # Valid per-user API key

        # Check global API key (legacy)
        if settings.api_key and x_api_key == settings.api_key:
            return  # Valid global API key

    # No valid authentication
    if settings.api_key or x_api_key or bearer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_optional_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    x_api_key: Optional[str] = Header(None),
) -> Optional[User]:
    """Get current user if authenticated, None otherwise.

    Useful for endpoints that work both with and without auth.
    """
    try:
        return get_current_user(db, token, bearer, x_api_key)
    except HTTPException:
        return None
