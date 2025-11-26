"""Telemetry event logging for product analytics."""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.db.models import TelemetryEvent


logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of telemetry events."""

    # User events
    USER_REGISTERED = "user.registered"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    ONBOARDING_STEP_COMPLETED = "onboarding.step_completed"
    ONBOARDING_COMPLETED = "onboarding.completed"

    # Portfolio events
    HOLDING_ADDED = "holding.added"
    HOLDING_UPDATED = "holding.updated"
    HOLDING_DELETED = "holding.deleted"
    HOLDINGS_IMPORTED = "holdings.imported"
    BROKER_LINKED = "broker.linked"
    BROKER_SYNCED = "broker.synced"

    # Rule events
    RULE_CREATED = "rule.created"
    RULE_UPDATED = "rule.updated"
    RULE_DELETED = "rule.deleted"
    RULE_ENABLED = "rule.enabled"
    RULE_DISABLED = "rule.disabled"
    STRATEGY_APPLIED = "strategy.applied"

    # Alert events
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_NOTIFIED = "alert.notified"
    ALERT_RATED = "alert.rated"
    ALERT_DISMISSED = "alert.dismissed"

    # Monitor events
    MONITOR_RUN_STARTED = "monitor.run_started"
    MONITOR_RUN_COMPLETED = "monitor.run_completed"

    # Dashboard events
    DASHBOARD_VIEWED = "dashboard.viewed"
    METRICS_VIEWED = "metrics.viewed"

    # API events
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"


class TelemetryLogger:
    """Logger for telemetry events."""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        event_type: EventType,
        user_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        event_meta: Optional[Dict[str, Any]] = None,
    ) -> TelemetryEvent:
        """Log a telemetry event.

        Args:
            event_type: Type of event
            user_id: ID of user associated with event (optional)
            properties: Event-specific properties (e.g., rule_id, symbol)
            event_meta: Additional metadata (e.g., source, client info)

        Returns:
            Created TelemetryEvent
        """
        event = TelemetryEvent(
            event_type=event_type.value,
            user_id=user_id,
            properties=properties or {},
            event_meta=event_meta or {},
            timestamp=datetime.utcnow(),
        )

        self.db.add(event)
        self.db.flush()

        logger.debug(
            f"Telemetry: {event_type.value} user={user_id} props={properties}"
        )

        return event

    # Convenience methods for common events

    def log_user_registered(self, user_id: str, email: str) -> TelemetryEvent:
        """Log user registration event."""
        return self.log(
            EventType.USER_REGISTERED,
            user_id=user_id,
            properties={"email_domain": email.split("@")[-1]},
        )

    def log_user_login(self, user_id: str) -> TelemetryEvent:
        """Log user login event."""
        return self.log(EventType.USER_LOGIN, user_id=user_id)

    def log_onboarding_step(
        self, user_id: str, step: int, skipped: bool = False
    ) -> TelemetryEvent:
        """Log onboarding step completion."""
        return self.log(
            EventType.ONBOARDING_STEP_COMPLETED,
            user_id=user_id,
            properties={"step": step, "skipped": skipped},
        )

    def log_alert_triggered(
        self,
        user_id: str,
        alert_id: str,
        rule_id: str,
        rule_type: str,
        symbol: str,
    ) -> TelemetryEvent:
        """Log alert triggered event."""
        return self.log(
            EventType.ALERT_TRIGGERED,
            user_id=user_id,
            properties={
                "alert_id": alert_id,
                "rule_id": rule_id,
                "rule_type": rule_type,
                "symbol": symbol,
            },
        )

    def log_alert_rated(
        self,
        user_id: str,
        alert_id: str,
        rating: str,
        rule_type: str,
        symbol: str,
    ) -> TelemetryEvent:
        """Log alert rating event."""
        return self.log(
            EventType.ALERT_RATED,
            user_id=user_id,
            properties={
                "alert_id": alert_id,
                "rating": rating,
                "rule_type": rule_type,
                "symbol": symbol,
            },
        )

    def log_rule_created(
        self,
        user_id: str,
        rule_id: str,
        rule_type: str,
        symbol: Optional[str],
    ) -> TelemetryEvent:
        """Log rule creation event."""
        return self.log(
            EventType.RULE_CREATED,
            user_id=user_id,
            properties={
                "rule_id": rule_id,
                "rule_type": rule_type,
                "symbol": symbol,
            },
        )

    def log_strategy_applied(
        self, user_id: str, strategy_id: str, rules_count: int
    ) -> TelemetryEvent:
        """Log strategy application event."""
        return self.log(
            EventType.STRATEGY_APPLIED,
            user_id=user_id,
            properties={
                "strategy_id": strategy_id,
                "rules_count": rules_count,
            },
        )

    def log_holdings_imported(
        self,
        user_id: str,
        source: str,
        count: int,
        created: int,
        updated: int,
    ) -> TelemetryEvent:
        """Log holdings import event."""
        return self.log(
            EventType.HOLDINGS_IMPORTED,
            user_id=user_id,
            properties={
                "source": source,
                "count": count,
                "created": created,
                "updated": updated,
            },
        )

    def log_monitor_run(
        self,
        user_id: str,
        alerts_triggered: int,
        rules_evaluated: int,
        holdings_checked: int,
    ) -> TelemetryEvent:
        """Log monitor run completion event."""
        return self.log(
            EventType.MONITOR_RUN_COMPLETED,
            user_id=user_id,
            properties={
                "alerts_triggered": alerts_triggered,
                "rules_evaluated": rules_evaluated,
                "holdings_checked": holdings_checked,
            },
        )


def get_telemetry_logger(db: Session) -> TelemetryLogger:
    """Factory function to get a TelemetryLogger instance."""
    return TelemetryLogger(db)
