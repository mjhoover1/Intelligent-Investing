"""Authentication service for user management."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from src.db.models import User, UserApiKey, NotificationSettings
from src.core.auth.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    generate_api_key,
    hash_api_key,
    verify_api_key,
)


class AuthService:
    """Service for user authentication and management."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address."""
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def register(
        self,
        email: str,
        password: str,
        is_admin: bool = False,
    ) -> Tuple[User, str]:
        """Register a new user.

        Args:
            email: User's email address
            password: Plain text password
            is_admin: Whether user should be an admin

        Returns:
            Tuple of (user, access_token)

        Raises:
            ValueError: If email already exists
        """
        # Check if email exists
        existing = self.get_user_by_email(email)
        if existing:
            raise ValueError(f"Email '{email}' is already registered")

        # Create user with hashed password
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            is_active=True,
            is_admin=is_admin,
        )
        self.db.add(user)
        self.db.flush()  # Get the user ID

        # Create default notification settings
        settings = NotificationSettings(
            user_id=user.id,
            telegram_enabled=False,
            console_enabled=True,
        )
        self.db.add(settings)
        self.db.commit()

        # Generate access token
        token = create_access_token(data={"sub": user.id})

        return user, token

    def login(self, email: str, password: str) -> Tuple[User, str]:
        """Authenticate a user and return access token.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            Tuple of (user, access_token)

        Raises:
            ValueError: If credentials are invalid
        """
        user = self.get_user_by_email(email)
        if not user:
            raise ValueError("Invalid email or password")

        if not user.password_hash:
            raise ValueError("User has no password set (legacy account)")

        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("User account is disabled")

        # Update last login
        user.last_login_at = datetime.utcnow()
        self.db.commit()

        # Generate access token
        token = create_access_token(data={"sub": user.id})

        return user, token

    def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change a user's password.

        Args:
            user: The user
            current_password: Current password for verification
            new_password: New password to set

        Raises:
            ValueError: If current password is wrong
        """
        if user.password_hash and not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")

        user.password_hash = get_password_hash(new_password)
        self.db.commit()

    def set_password(self, user: User, password: str) -> None:
        """Set a user's password (admin function, no verification).

        Args:
            user: The user
            password: New password to set
        """
        user.password_hash = get_password_hash(password)
        self.db.commit()

    # API Key Management

    def create_api_key(
        self,
        user: User,
        name: str,
        expires_at: Optional[datetime] = None,
    ) -> Tuple[UserApiKey, str]:
        """Create a new API key for a user.

        Args:
            user: The user
            name: Friendly name for the key
            expires_at: Optional expiration datetime

        Returns:
            Tuple of (api_key_record, plain_api_key)
            Note: The plain key is only returned once!
        """
        # Generate and hash the key
        plain_key = generate_api_key()
        hashed_key = hash_api_key(plain_key)

        api_key = UserApiKey(
            user_id=user.id,
            key_hash=hashed_key,
            name=name,
            expires_at=expires_at,
            is_active=True,
        )
        self.db.add(api_key)
        self.db.commit()

        return api_key, plain_key

    def validate_api_key(self, plain_key: str) -> Optional[User]:
        """Validate an API key and return the associated user.

        Args:
            plain_key: The plain API key

        Returns:
            User if key is valid, None otherwise
        """
        # Get all active API keys
        api_keys = self.db.query(UserApiKey).filter(
            UserApiKey.is_active == True  # noqa: E712
        ).all()

        for key in api_keys:
            # Check expiration
            if key.expires_at and key.expires_at < datetime.utcnow():
                continue

            # Verify the key
            if verify_api_key(plain_key, key.key_hash):
                # Update last used
                key.last_used_at = datetime.utcnow()
                self.db.commit()

                # Return the user
                return self.get_user_by_id(key.user_id)

        return None

    def list_api_keys(self, user: User) -> list:
        """List all API keys for a user.

        Args:
            user: The user

        Returns:
            List of UserApiKey records (without the actual key values)
        """
        return self.db.query(UserApiKey).filter(
            UserApiKey.user_id == user.id
        ).all()

    def revoke_api_key(self, user: User, key_id: str) -> bool:
        """Revoke an API key.

        Args:
            user: The user (for ownership verification)
            key_id: The API key ID

        Returns:
            True if revoked, False if not found
        """
        api_key = self.db.query(UserApiKey).filter(
            UserApiKey.id == key_id,
            UserApiKey.user_id == user.id,
        ).first()

        if not api_key:
            return False

        api_key.is_active = False
        self.db.commit()
        return True

    def delete_api_key(self, user: User, key_id: str) -> bool:
        """Permanently delete an API key.

        Args:
            user: The user (for ownership verification)
            key_id: The API key ID

        Returns:
            True if deleted, False if not found
        """
        api_key = self.db.query(UserApiKey).filter(
            UserApiKey.id == key_id,
            UserApiKey.user_id == user.id,
        ).first()

        if not api_key:
            return False

        self.db.delete(api_key)
        self.db.commit()
        return True


def get_auth_service(db: Session) -> AuthService:
    """Factory function to get an AuthService instance."""
    return AuthService(db)
