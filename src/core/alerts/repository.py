"""Alert repository for CRUD operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session


def _utcnow() -> datetime:
    """Get current UTC time as naive datetime for database compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

from src.db.models import Alert, Rule, User
from src.config import get_settings

settings = get_settings()


class AlertRepository:
    """Repository for Alert CRUD operations."""

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

    def create(
        self,
        user_id: str,
        rule_id: str,
        symbol: str,
        message: str,
        holding_id: Optional[str] = None,
        ai_summary: Optional[str] = None,
    ) -> Alert:
        """Create a new alert.

        Args:
            user_id: User ID
            rule_id: Rule ID that triggered
            symbol: Stock symbol
            message: Alert message
            holding_id: Optional holding ID
            ai_summary: Optional AI-generated context

        Returns:
            Created alert
        """
        alert = Alert(
            user_id=user_id,
            rule_id=rule_id,
            holding_id=holding_id,
            symbol=symbol.upper(),
            message=message,
            ai_summary=ai_summary,
            triggered_at=_utcnow(),
        )
        self.db.add(alert)
        self.db.flush()
        return alert

    def get_by_id(self, alert_id: str, user_id: Optional[str] = None) -> Optional[Alert]:
        """Get an alert by ID.

        Args:
            alert_id: Alert ID
            user_id: Optional user ID for ownership verification

        Returns:
            Alert if found (and owned by user if user_id provided), None otherwise
        """
        query = self.db.query(Alert).filter_by(id=alert_id)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        return query.first()

    def get_recent(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Alert]:
        """Get recent alerts for a user.

        Args:
            user_id: User ID. If None, uses default user.
            limit: Maximum number of alerts to return

        Returns:
            List of alerts ordered by triggered_at desc
        """
        if user_id is None:
            user = self._get_or_create_default_user()
            user_id = user.id

        return (
            self.db.query(Alert)
            .filter_by(user_id=user_id)
            .order_by(Alert.triggered_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_symbol(
        self,
        symbol: str,
        user_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Alert]:
        """Get alerts for a specific symbol.

        Args:
            symbol: Stock symbol
            user_id: User ID. If None, uses default user.
            limit: Maximum number of alerts

        Returns:
            List of alerts for the symbol
        """
        symbol = symbol.upper()
        if user_id is None:
            user = self._get_or_create_default_user()
            user_id = user.id

        return (
            self.db.query(Alert)
            .filter_by(user_id=user_id, symbol=symbol)
            .order_by(Alert.triggered_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_rule(
        self,
        rule_id: str,
        user_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Alert]:
        """Get alerts for a specific rule.

        Args:
            rule_id: Rule ID
            user_id: User ID. If None, uses default user.
            limit: Maximum number of alerts

        Returns:
            List of alerts for the rule
        """
        if user_id is None:
            user = self._get_or_create_default_user()
            user_id = user.id

        return (
            self.db.query(Alert)
            .filter_by(rule_id=rule_id, user_id=user_id)
            .order_by(Alert.triggered_at.desc())
            .limit(limit)
            .all()
        )

    def mark_notified(self, alert_id: str) -> bool:
        """Mark an alert as notified.

        Args:
            alert_id: Alert ID

        Returns:
            True if updated, False if not found
        """
        alert = self.get_by_id(alert_id)
        if not alert:
            return False

        alert.notified = True
        self.db.flush()
        return True

    def update_ai_summary(self, alert_id: str, ai_summary: str) -> bool:
        """Update the AI summary for an alert.

        Args:
            alert_id: Alert ID
            ai_summary: AI-generated summary

        Returns:
            True if updated, False if not found
        """
        alert = self.get_by_id(alert_id)
        if not alert:
            return False

        alert.ai_summary = ai_summary
        self.db.flush()
        return True

    def delete(self, alert_id: str) -> bool:
        """Delete an alert.

        Args:
            alert_id: Alert ID

        Returns:
            True if deleted, False if not found
        """
        alert = self.get_by_id(alert_id)
        if not alert:
            return False

        self.db.delete(alert)
        self.db.flush()
        return True

    def clear_all(self, user_id: Optional[str] = None) -> int:
        """Clear all alerts for a user.

        Args:
            user_id: User ID. If None, uses default user.

        Returns:
            Number of alerts deleted
        """
        if user_id is None:
            user = self._get_or_create_default_user()
            user_id = user.id

        count = self.db.query(Alert).filter_by(user_id=user_id).delete()
        self.db.flush()
        return count
