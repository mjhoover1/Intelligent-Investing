"""Rule repository for CRUD operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session


def _utcnow() -> datetime:
    """Get current UTC time as naive datetime for database compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

from src.db.models import Rule, User
from src.config import get_settings
from .models import RuleType

settings = get_settings()


class RuleRepository:
    """Repository for Rule CRUD operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def _get_or_create_default_user(self) -> User:
        """Get or create the default user for MVP mode."""
        user = self.db.query(User).filter_by(email=settings.default_user_email).first()
        if not user:
            user = User(email=settings.default_user_email)
            self.db.add(user)
            self.db.flush()
        return user

    def get_all(self, user_id: Optional[str] = None) -> List[Rule]:
        """Get all rules for a user.

        Args:
            user_id: User ID. If None, uses default user.

        Returns:
            List of rules
        """
        if user_id is None:
            user = self._get_or_create_default_user()
            user_id = user.id
        return self.db.query(Rule).filter_by(user_id=user_id).all()

    def get_active(self, user_id: Optional[str] = None) -> List[Rule]:
        """Get all enabled rules for a user.

        Args:
            user_id: User ID. If None, uses default user.

        Returns:
            List of enabled rules
        """
        if user_id is None:
            user = self._get_or_create_default_user()
            user_id = user.id
        return self.db.query(Rule).filter_by(user_id=user_id, enabled=True).all()

    def get_by_id(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        return self.db.query(Rule).filter_by(id=rule_id).first()

    def get_by_name(self, name: str, user_id: Optional[str] = None) -> Optional[Rule]:
        """Get a rule by name.

        Args:
            name: Rule name
            user_id: User ID. If None, uses default user.

        Returns:
            Rule or None
        """
        if user_id is None:
            user = self._get_or_create_default_user()
            user_id = user.id
        return self.db.query(Rule).filter_by(user_id=user_id, name=name).first()

    def create(
        self,
        name: str,
        rule_type: RuleType,
        threshold: float,
        symbol: Optional[str] = None,
        enabled: bool = True,
        cooldown_minutes: int = 60,
        user_id: Optional[str] = None,
    ) -> Rule:
        """Create a new rule.

        Args:
            name: Rule name
            rule_type: Type of rule condition
            threshold: Threshold value
            symbol: Optional symbol (None = all holdings)
            enabled: Whether rule is enabled
            cooldown_minutes: Cooldown between triggers
            user_id: User ID. If None, uses default user.

        Returns:
            Created rule
        """
        if user_id is None:
            user = self._get_or_create_default_user()
            user_id = user.id

        # Normalize symbol
        if symbol:
            symbol = symbol.upper()

        rule = Rule(
            user_id=user_id,
            name=name,
            rule_type=rule_type.value,
            threshold=threshold,
            symbol=symbol,
            enabled=enabled,
            cooldown_minutes=cooldown_minutes,
        )
        self.db.add(rule)
        self.db.flush()
        return rule

    def update(
        self,
        rule_id: str,
        name: Optional[str] = None,
        threshold: Optional[float] = None,
        symbol: Optional[str] = None,
        enabled: Optional[bool] = None,
        cooldown_minutes: Optional[int] = None,
    ) -> Optional[Rule]:
        """Update a rule.

        Args:
            rule_id: Rule ID
            name: New name
            threshold: New threshold
            symbol: New symbol
            enabled: New enabled status
            cooldown_minutes: New cooldown

        Returns:
            Updated rule or None if not found
        """
        rule = self.get_by_id(rule_id)
        if not rule:
            return None

        if name is not None:
            rule.name = name
        if threshold is not None:
            rule.threshold = threshold
        if symbol is not None:
            rule.symbol = symbol.upper() if symbol else None
        if enabled is not None:
            rule.enabled = enabled
        if cooldown_minutes is not None:
            rule.cooldown_minutes = cooldown_minutes

        self.db.flush()
        return rule

    def delete(self, rule_id: str) -> bool:
        """Delete a rule.

        Args:
            rule_id: Rule ID

        Returns:
            True if deleted, False if not found
        """
        rule = self.get_by_id(rule_id)
        if not rule:
            return False

        self.db.delete(rule)
        self.db.flush()
        return True

    def delete_by_name(self, name: str, user_id: Optional[str] = None) -> bool:
        """Delete a rule by name.

        Args:
            name: Rule name
            user_id: User ID. If None, uses default user.

        Returns:
            True if deleted, False if not found
        """
        rule = self.get_by_name(name, user_id)
        if not rule:
            return False

        self.db.delete(rule)
        self.db.flush()
        return True

    def update_last_triggered(self, rule_id: str) -> None:
        """Update the last_triggered_at timestamp for a rule.

        Args:
            rule_id: Rule ID
        """
        rule = self.get_by_id(rule_id)
        if rule:
            rule.last_triggered_at = _utcnow()
            self.db.flush()
