"""Security utilities for password hashing and JWT tokens."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: The plain text password
        hashed_password: The hashed password to compare against

    Returns:
        True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token.

    Args:
        data: Data to encode in the token (should include 'sub' for user ID)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc).replace(tzinfo=None) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})

    # Use API_KEY as secret for JWT (or a dedicated JWT_SECRET if you add one)
    secret_key = settings.api_key or "dev-secret-key-change-in-production"

    return jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT token to decode

    Returns:
        Decoded token data or None if invalid
    """
    try:
        secret_key = settings.api_key or "dev-secret-key-change-in-production"
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_api_key() -> str:
    """Generate a new API key.

    Returns:
        A secure random API key (32 bytes, URL-safe base64)
    """
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage.

    Args:
        api_key: The plain API key

    Returns:
        Hashed API key
    """
    return pwd_context.hash(api_key)


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash.

    Args:
        plain_key: The plain API key
        hashed_key: The hashed key to compare against

    Returns:
        True if key matches
    """
    return pwd_context.verify(plain_key, hashed_key)
