"""Monitor service - runs evaluation cycles."""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import Alert, User
from src.core.rules.engine import RuleEngine
from src.core.alerts.service import AlertService
from src.core.alerts.notifier import console_notifier
from src.data.market.provider import MarketDataProvider, market_data
from src.ai.context.generator import get_context_generator
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MonitorService:
    """Service for running monitoring cycles."""

    def __init__(
        self,
        market_provider: Optional[MarketDataProvider] = None,
        use_ai: bool = False,
        ignore_cooldown: bool = False,
    ):
        """Initialize the monitor service.

        Args:
            market_provider: Market data provider (defaults to global instance)
            use_ai: Whether to generate AI context for alerts
            ignore_cooldown: Whether to ignore rule cooldowns
        """
        self.market_provider = market_provider or market_data
        self.use_ai = use_ai
        self.ignore_cooldown = ignore_cooldown

    def run_cycle(self, db: Session, user_id: str) -> List[Alert]:
        """Run a single monitoring cycle.

        Args:
            db: Database session
            user_id: User ID to monitor

        Returns:
            List of created alerts
        """
        logger.info("Starting monitoring cycle")

        # Create rule engine
        engine = RuleEngine(
            market_provider=self.market_provider,
            cooldown_enabled=not self.ignore_cooldown,
        )

        # Evaluate all rules
        results = engine.evaluate_all(db, user_id)

        if not results:
            logger.info("No rules triggered this cycle")
            return []

        logger.info(f"{len(results)} rule(s) triggered")

        # Set up context generator if AI is enabled
        context_generator = None
        if self.use_ai:
            context_generator = get_context_generator()

        # Create alert service
        service = AlertService(
            db=db,
            notifier=console_notifier,
            context_generator=context_generator,
            generate_ai_context=self.use_ai,
        )

        # Process results into alerts
        alerts = service.process_evaluation_results(
            results=results,
            user_id=user_id,
            notify=True,
        )

        logger.info(f"Created {len(alerts)} alert(s)")
        return alerts


def get_default_user_id(db: Session) -> Optional[str]:
    """Get or create the default user and return their ID.

    Args:
        db: Database session

    Returns:
        User ID or None if creation failed
    """
    user = db.query(User).filter_by(email=settings.default_user_email).first()
    if not user:
        user = User(email=settings.default_user_email)
        db.add(user)
        db.flush()
    return user.id


def run_monitor_cycle(
    use_ai: bool = False,
    ignore_cooldown: bool = False,
) -> List[Alert]:
    """Run a single monitoring cycle (convenience function).

    Args:
        use_ai: Whether to generate AI context
        ignore_cooldown: Whether to ignore cooldowns

    Returns:
        List of created alerts
    """
    with get_db() as db:
        user_id = get_default_user_id(db)
        if not user_id:
            logger.error("Could not get default user")
            return []

        monitor = MonitorService(
            use_ai=use_ai,
            ignore_cooldown=ignore_cooldown,
        )

        return monitor.run_cycle(db, user_id)
