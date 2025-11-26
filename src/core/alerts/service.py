"""Alert service - orchestrates alert creation from evaluation results."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy.orm import Session

from src.db.models import Alert, Rule
from src.core.rules.models import EvaluationResult
from .repository import AlertRepository
from .notifier import BaseNotifier, console_notifier
from .models import AlertContextData

if TYPE_CHECKING:
    from src.ai.context.generator import ContextGenerator


class AlertService:
    """Service for creating and managing alerts from evaluation results."""

    def __init__(
        self,
        db: Session,
        notifier: Optional[BaseNotifier] = None,
        context_generator: Optional["ContextGenerator"] = None,
        generate_ai_context: bool = True,
    ):
        """Initialize the alert service.

        Args:
            db: Database session
            notifier: Notifier to use (defaults to console)
            context_generator: AI context generator (optional)
            generate_ai_context: Whether to generate AI summaries
        """
        self.db = db
        self.repo = AlertRepository(db)
        self.notifier = notifier or console_notifier
        self.context_generator = context_generator
        self.generate_ai_context = generate_ai_context

    def process_evaluation_results(
        self,
        results: List[EvaluationResult],
        user_id: str,
        notify: bool = True,
    ) -> List[Alert]:
        """Process evaluation results and create alerts.

        Args:
            results: List of triggered evaluation results
            user_id: User ID
            notify: Whether to send notifications

        Returns:
            List of created alerts
        """
        alerts = []

        for result in results:
            if not result.triggered:
                continue

            # Create the alert
            alert = self._create_alert_from_result(result, user_id)
            alerts.append(alert)

            # Update rule's last_triggered_at
            self._update_rule_triggered(result.rule_id)

            # Generate AI context if enabled
            if self.generate_ai_context and self.context_generator:
                ai_summary = self._generate_context(result)
                if ai_summary:
                    alert.ai_summary = ai_summary

            # Send notification
            if notify:
                self.notifier.notify(alert)

        return alerts

    def _create_alert_from_result(
        self,
        result: EvaluationResult,
        user_id: str,
    ) -> Alert:
        """Create an alert from an evaluation result.

        Args:
            result: Evaluation result
            user_id: User ID

        Returns:
            Created alert
        """
        # Build message
        message = f"{result.rule_name}: {result.reason}"

        alert = self.repo.create(
            user_id=user_id,
            rule_id=result.rule_id,
            holding_id=result.holding_id,
            symbol=result.symbol,
            message=message,
        )

        return alert

    def _update_rule_triggered(self, rule_id: str) -> None:
        """Update a rule's last_triggered_at timestamp.

        Args:
            rule_id: Rule ID
        """
        rule = self.db.query(Rule).filter_by(id=rule_id).first()
        if rule:
            rule.last_triggered_at = datetime.utcnow()

    def _generate_context(self, result: EvaluationResult) -> Optional[str]:
        """Generate AI context for an evaluation result.

        Args:
            result: Evaluation result

        Returns:
            AI-generated context or None
        """
        if not self.context_generator:
            return None

        try:
            # Calculate percent change if we have cost basis
            percent_change = None
            if result.cost_basis and result.cost_basis > 0:
                percent_change = (
                    (result.current_price - result.cost_basis) / result.cost_basis * 100
                )

            context_data = AlertContextData(
                symbol=result.symbol,
                rule_name=result.rule_name,
                rule_type=result.rule_type.value,
                threshold=result.threshold,
                current_price=result.current_price,
                cost_basis=result.cost_basis,
                percent_change=percent_change,
                message=result.reason,
            )

            return self.context_generator.generate(context_data)

        except Exception:
            # Don't fail alert creation if AI fails
            return None

    def create_test_alert(
        self,
        user_id: str,
        symbol: str = "TEST",
        message: str = "This is a test alert",
        notify: bool = True,
    ) -> Alert:
        """Create a test alert for verification.

        Args:
            user_id: User ID
            symbol: Symbol for test alert
            message: Test message
            notify: Whether to send notification

        Returns:
            Created test alert
        """
        # We need a rule_id, so get or create a test rule
        from src.core.rules.repository import RuleRepository
        from src.core.rules.models import RuleType

        rule_repo = RuleRepository(self.db)

        # Check for existing test rule
        test_rule = rule_repo.get_by_name("__test_rule__", user_id)
        if not test_rule:
            test_rule = rule_repo.create(
                name="__test_rule__",
                rule_type=RuleType.PRICE_BELOW_VALUE,
                threshold=0,
                enabled=False,  # Keep disabled
                user_id=user_id,
            )

        alert = self.repo.create(
            user_id=user_id,
            rule_id=test_rule.id,
            symbol=symbol.upper(),
            message=message,
        )

        if notify:
            self.notifier.notify(alert)

        return alert
