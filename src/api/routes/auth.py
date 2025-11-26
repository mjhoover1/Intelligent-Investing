"""Authentication API routes."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_current_user
from src.core.auth import AuthService, get_auth_service
from src.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limiter for auth endpoints
limiter = Limiter(key_func=get_remote_address)


# Request/Response Models

class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User info response."""

    id: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login_at: Optional[datetime]


class AuthResponse(BaseModel):
    """Authentication response with user and token."""

    user: UserResponse
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    current_password: str
    new_password: str


class CreateApiKeyRequest(BaseModel):
    """Create API key request."""

    name: str
    expires_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    """API key response."""

    id: str
    name: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]


class ApiKeyCreatedResponse(BaseModel):
    """Response when API key is created (includes plain key)."""

    id: str
    name: str
    api_key: str  # Only returned once!
    message: str = "Store this key securely - it won't be shown again"


# Public Routes (no auth required)

@router.post("/register", response_model=AuthResponse)
@limiter.limit("5/minute")  # 5 registrations per minute per IP
def register(
    request_obj: Request,
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Register a new user account."""
    auth_service = get_auth_service(db)

    try:
        user, token = auth_service.register(
            email=request.email,
            password=request.password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        ),
        access_token=token,
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")  # 10 login attempts per minute per IP
def login(
    request_obj: Request,
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """Login with email and password."""
    auth_service = get_auth_service(db)

    try:
        user, token = auth_service.login(
            email=request.email,
            password=request.password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        ),
        access_token=token,
    )


@router.post("/token", response_model=TokenResponse)
@limiter.limit("10/minute")  # 10 token requests per minute per IP
def login_for_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 compatible token endpoint (for Swagger UI)."""
    auth_service = get_auth_service(db)

    try:
        user, token = auth_service.login(
            email=form_data.username,  # OAuth2 uses 'username' field
            password=form_data.password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=token)


# Protected Routes (auth required)

@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    user: User = Depends(get_current_user),
):
    """Get current user info."""
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Change current user's password."""
    auth_service = get_auth_service(db)

    try:
        auth_service.change_password(
            user=user,
            current_password=request.current_password,
            new_password=request.new_password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {"status": "ok", "message": "Password changed successfully"}


# API Key Management

@router.post("/api-keys", response_model=ApiKeyCreatedResponse)
def create_api_key(
    request: CreateApiKeyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new API key for programmatic access."""
    auth_service = get_auth_service(db)

    api_key_record, plain_key = auth_service.create_api_key(
        user=user,
        name=request.name,
        expires_at=request.expires_at,
    )

    return ApiKeyCreatedResponse(
        id=api_key_record.id,
        name=api_key_record.name,
        api_key=plain_key,
    )


@router.get("/api-keys", response_model=List[ApiKeyResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all API keys for current user."""
    auth_service = get_auth_service(db)

    keys = auth_service.list_api_keys(user)

    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            is_active=k.is_active,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
            expires_at=k.expires_at,
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Revoke an API key."""
    auth_service = get_auth_service(db)

    if not auth_service.revoke_api_key(user, key_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return {"status": "ok", "message": "API key revoked"}
