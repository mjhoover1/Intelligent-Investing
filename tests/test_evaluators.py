"""Tests for rule evaluators."""

import pytest

from src.core.rules.models import RuleType
from src.core.rules.evaluators import (
    get_evaluator,
    PriceBelowCostPctEvaluator,
    PriceAboveCostPctEvaluator,
    PriceBelowValueEvaluator,
    PriceAboveValueEvaluator,
    RSIBelowValueEvaluator,
    RSIAboveValueEvaluator,
)


class TestPriceBelowCostPctEvaluator:
    """Tests for price_below_cost_pct rule type."""

    def test_triggers_when_price_below_threshold(self):
        """Should trigger when price is X% below cost basis."""
        evaluator = PriceBelowCostPctEvaluator()
        # Cost basis $100, price $75 = 25% below
        assert evaluator.evaluate(
            current_price=75.0,
            cost_basis=100.0,
            threshold=20.0,  # 20% threshold
        ) is True

    def test_does_not_trigger_when_price_above_threshold(self):
        """Should not trigger when price is within threshold."""
        evaluator = PriceBelowCostPctEvaluator()
        # Cost basis $100, price $90 = 10% below
        assert evaluator.evaluate(
            current_price=90.0,
            cost_basis=100.0,
            threshold=20.0,  # 20% threshold
        ) is False

    def test_does_not_trigger_when_price_above_cost(self):
        """Should not trigger when price is above cost basis."""
        evaluator = PriceBelowCostPctEvaluator()
        assert evaluator.evaluate(
            current_price=110.0,
            cost_basis=100.0,
            threshold=20.0,
        ) is False

    def test_format_reason(self):
        """Should format reason correctly."""
        evaluator = PriceBelowCostPctEvaluator()
        reason = evaluator.format_reason(
            current_price=75.0,
            cost_basis=100.0,
            threshold=20.0,
        )
        assert "$75.00" in reason
        assert "25.0%" in reason
        assert "$100.00" in reason


class TestPriceAboveCostPctEvaluator:
    """Tests for price_above_cost_pct rule type."""

    def test_triggers_when_price_above_threshold(self):
        """Should trigger when price is X% above cost basis."""
        evaluator = PriceAboveCostPctEvaluator()
        # Cost basis $100, price $150 = 50% above
        assert evaluator.evaluate(
            current_price=150.0,
            cost_basis=100.0,
            threshold=40.0,  # 40% threshold
        ) is True

    def test_does_not_trigger_when_price_below_threshold(self):
        """Should not trigger when gain is below threshold."""
        evaluator = PriceAboveCostPctEvaluator()
        # Cost basis $100, price $120 = 20% above
        assert evaluator.evaluate(
            current_price=120.0,
            cost_basis=100.0,
            threshold=40.0,  # 40% threshold
        ) is False

    def test_does_not_trigger_when_price_below_cost(self):
        """Should not trigger when price is below cost basis."""
        evaluator = PriceAboveCostPctEvaluator()
        assert evaluator.evaluate(
            current_price=90.0,
            cost_basis=100.0,
            threshold=40.0,
        ) is False


class TestPriceBelowValueEvaluator:
    """Tests for price_below_value rule type."""

    def test_triggers_when_price_below_value(self):
        """Should trigger when price drops below absolute value."""
        evaluator = PriceBelowValueEvaluator()
        assert evaluator.evaluate(
            current_price=95.0,
            cost_basis=100.0,  # Ignored for this type
            threshold=100.0,  # Alert when below $100
        ) is True

    def test_does_not_trigger_when_price_above_value(self):
        """Should not trigger when price is above threshold."""
        evaluator = PriceBelowValueEvaluator()
        assert evaluator.evaluate(
            current_price=105.0,
            cost_basis=100.0,
            threshold=100.0,
        ) is False


class TestPriceAboveValueEvaluator:
    """Tests for price_above_value rule type."""

    def test_triggers_when_price_above_value(self):
        """Should trigger when price rises above absolute value."""
        evaluator = PriceAboveValueEvaluator()
        assert evaluator.evaluate(
            current_price=155.0,
            cost_basis=100.0,  # Ignored for this type
            threshold=150.0,  # Alert when above $150
        ) is True

    def test_does_not_trigger_when_price_below_value(self):
        """Should not trigger when price is below threshold."""
        evaluator = PriceAboveValueEvaluator()
        assert evaluator.evaluate(
            current_price=145.0,
            cost_basis=100.0,
            threshold=150.0,
        ) is False


class TestRSIBelowValueEvaluator:
    """Tests for rsi_below_value rule type (oversold signal)."""

    def test_triggers_when_rsi_below_threshold(self):
        """Should trigger when RSI is below threshold."""
        evaluator = RSIBelowValueEvaluator()
        assert evaluator.evaluate(
            current_price=50.0,
            cost_basis=100.0,
            threshold=30.0,  # Alert when RSI < 30
            indicator_value=25.0,  # RSI at 25 (oversold)
        ) is True

    def test_does_not_trigger_when_rsi_above_threshold(self):
        """Should not trigger when RSI is above threshold."""
        evaluator = RSIBelowValueEvaluator()
        assert evaluator.evaluate(
            current_price=50.0,
            cost_basis=100.0,
            threshold=30.0,
            indicator_value=45.0,  # RSI at 45 (normal)
        ) is False

    def test_does_not_trigger_when_no_indicator_value(self):
        """Should not trigger when indicator value is None."""
        evaluator = RSIBelowValueEvaluator()
        assert evaluator.evaluate(
            current_price=50.0,
            cost_basis=100.0,
            threshold=30.0,
            indicator_value=None,
        ) is False

    def test_format_reason(self):
        """Should format reason correctly with oversold zone."""
        evaluator = RSIBelowValueEvaluator()
        reason = evaluator.format_reason(
            current_price=50.0,
            cost_basis=100.0,
            threshold=30.0,
            indicator_value=25.0,
        )
        assert "RSI 25.0" in reason
        assert "oversold" in reason
        assert "$50.00" in reason


class TestRSIAboveValueEvaluator:
    """Tests for rsi_above_value rule type (overbought signal)."""

    def test_triggers_when_rsi_above_threshold(self):
        """Should trigger when RSI is above threshold."""
        evaluator = RSIAboveValueEvaluator()
        assert evaluator.evaluate(
            current_price=150.0,
            cost_basis=100.0,
            threshold=70.0,  # Alert when RSI > 70
            indicator_value=75.0,  # RSI at 75 (overbought)
        ) is True

    def test_does_not_trigger_when_rsi_below_threshold(self):
        """Should not trigger when RSI is below threshold."""
        evaluator = RSIAboveValueEvaluator()
        assert evaluator.evaluate(
            current_price=150.0,
            cost_basis=100.0,
            threshold=70.0,
            indicator_value=55.0,  # RSI at 55 (normal)
        ) is False

    def test_does_not_trigger_when_no_indicator_value(self):
        """Should not trigger when indicator value is None."""
        evaluator = RSIAboveValueEvaluator()
        assert evaluator.evaluate(
            current_price=150.0,
            cost_basis=100.0,
            threshold=70.0,
            indicator_value=None,
        ) is False

    def test_format_reason(self):
        """Should format reason correctly with overbought zone."""
        evaluator = RSIAboveValueEvaluator()
        reason = evaluator.format_reason(
            current_price=150.0,
            cost_basis=100.0,
            threshold=70.0,
            indicator_value=75.0,
        )
        assert "RSI 75.0" in reason
        assert "overbought" in reason
        assert "$150.00" in reason


class TestGetEvaluator:
    """Tests for get_evaluator factory function."""

    def test_returns_correct_evaluator_for_each_type(self):
        """Should return correct evaluator for each rule type."""
        assert isinstance(
            get_evaluator(RuleType.PRICE_BELOW_COST_PCT),
            PriceBelowCostPctEvaluator,
        )
        assert isinstance(
            get_evaluator(RuleType.PRICE_ABOVE_COST_PCT),
            PriceAboveCostPctEvaluator,
        )
        assert isinstance(
            get_evaluator(RuleType.PRICE_BELOW_VALUE),
            PriceBelowValueEvaluator,
        )
        assert isinstance(
            get_evaluator(RuleType.PRICE_ABOVE_VALUE),
            PriceAboveValueEvaluator,
        )
        assert isinstance(
            get_evaluator(RuleType.RSI_BELOW_VALUE),
            RSIBelowValueEvaluator,
        )
        assert isinstance(
            get_evaluator(RuleType.RSI_ABOVE_VALUE),
            RSIAboveValueEvaluator,
        )
