"""Tests for AlertService."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from src.core.alerts.service import AlertService
from src.core.alerts.repository import AlertRepository
from src.core.rules.models import EvaluationResult, RuleType
from src.core.rules.repository import RuleRepository


class TestAlertService:
    """Tests for AlertService."""

    def test_process_evaluation_results_creates_alert(self):
        """Should create an alert from evaluation result."""
        # Set up mock database session
        mock_db = MagicMock()
        mock_notifier = Mock()
        mock_notifier.notify = Mock()

        # Create service
        service = AlertService(
            db=mock_db,
            notifier=mock_notifier,
            generate_ai_context=False,
        )

        # Create a fake evaluation result
        result = EvaluationResult(
            rule_id="rule-123",
            rule_name="Test Rule",
            rule_type=RuleType.PRICE_BELOW_COST_PCT,
            symbol="AAPL",
            triggered=True,
            reason="Price $90 is 10% below cost basis $100",
            current_price=90.0,
            cost_basis=100.0,
            threshold=10.0,
            holding_id="holding-456",
        )

        # Mock the rule query to return a rule with update capability
        mock_rule = Mock()
        mock_rule.last_triggered_at = None
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_rule

        # Process the result
        alerts = service.process_evaluation_results(
            results=[result],
            user_id="user-789",
            notify=True,
        )

        # Verify alert was created
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.symbol == "AAPL"
        assert alert.rule_id == "rule-123"
        assert "Test Rule" in alert.message

        # Verify rule's last_triggered_at was updated
        assert mock_rule.last_triggered_at is not None

        # Verify notifier was called
        mock_notifier.notify.assert_called_once()

    def test_creates_test_alert(self):
        """Should create a test alert."""
        mock_db = MagicMock()
        mock_notifier = Mock()

        service = AlertService(db=mock_db, notifier=mock_notifier)

        # Create test alert
        alert = service.create_test_alert(
            user_id="user-123",
            symbol="TEST",
            message="Test message",
            notify=False,
        )

        assert alert.symbol == "TEST"
        assert alert.message == "Test message"
        assert alert.user_id == "user-123"
