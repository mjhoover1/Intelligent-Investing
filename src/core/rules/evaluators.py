"""Condition evaluators for different rule types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional

from .models import RuleType


class ConditionEvaluator(ABC):
    """Abstract base class for condition evaluators."""

    @abstractmethod
    def evaluate(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> bool:
        """Evaluate if the condition is met.

        Args:
            current_price: Current market price
            cost_basis: Cost basis per share (may be None for some rule types)
            threshold: Rule threshold value
            indicator_value: Optional indicator value (RSI, etc.)

        Returns:
            True if condition is triggered
        """
        ...

    @abstractmethod
    def format_reason(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> str:
        """Generate human-readable reason for the trigger.

        Args:
            current_price: Current market price
            cost_basis: Cost basis per share
            threshold: Rule threshold value
            indicator_value: Optional indicator value

        Returns:
            Formatted reason string
        """
        ...


class PriceBelowCostPctEvaluator(ConditionEvaluator):
    """Evaluates if price has dropped X% below cost basis."""

    def evaluate(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> bool:
        if cost_basis is None or cost_basis == 0:
            return False
        drop_pct = (cost_basis - current_price) / cost_basis * 100
        return drop_pct >= threshold

    def format_reason(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> str:
        if cost_basis is None or cost_basis == 0:
            return "No cost basis available"
        drop_pct = (cost_basis - current_price) / cost_basis * 100
        return f"Price ${current_price:.2f} is {drop_pct:.1f}% below cost basis ${cost_basis:.2f} (threshold: {threshold}%)"


class PriceAboveCostPctEvaluator(ConditionEvaluator):
    """Evaluates if price has risen X% above cost basis."""

    def evaluate(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> bool:
        if cost_basis is None or cost_basis == 0:
            return False
        gain_pct = (current_price - cost_basis) / cost_basis * 100
        return gain_pct >= threshold

    def format_reason(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> str:
        if cost_basis is None or cost_basis == 0:
            return "No cost basis available"
        gain_pct = (current_price - cost_basis) / cost_basis * 100
        return f"Price ${current_price:.2f} is {gain_pct:.1f}% above cost basis ${cost_basis:.2f} (threshold: {threshold}%)"


class PriceBelowValueEvaluator(ConditionEvaluator):
    """Evaluates if price has dropped below a specific value."""

    def evaluate(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> bool:
        return current_price <= threshold

    def format_reason(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> str:
        return f"Price ${current_price:.2f} dropped below target ${threshold:.2f}"


class PriceAboveValueEvaluator(ConditionEvaluator):
    """Evaluates if price has risen above a specific value."""

    def evaluate(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> bool:
        return current_price >= threshold

    def format_reason(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> str:
        return f"Price ${current_price:.2f} rose above target ${threshold:.2f}"


class RSIBelowValueEvaluator(ConditionEvaluator):
    """Evaluates if RSI has dropped below a threshold (oversold signal)."""

    def evaluate(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> bool:
        if indicator_value is None:
            return False
        return indicator_value <= threshold

    def format_reason(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> str:
        if indicator_value is None:
            return "RSI data unavailable"
        zone = "oversold" if indicator_value < 30 else "approaching oversold"
        return f"RSI {indicator_value:.1f} dropped below {threshold:.0f} ({zone}) at price ${current_price:.2f}"


class RSIAboveValueEvaluator(ConditionEvaluator):
    """Evaluates if RSI has risen above a threshold (overbought signal)."""

    def evaluate(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> bool:
        if indicator_value is None:
            return False
        return indicator_value >= threshold

    def format_reason(
        self,
        current_price: float,
        cost_basis: Optional[float],
        threshold: float,
        indicator_value: Optional[float] = None,
    ) -> str:
        if indicator_value is None:
            return "RSI data unavailable"
        zone = "overbought" if indicator_value > 70 else "approaching overbought"
        return f"RSI {indicator_value:.1f} rose above {threshold:.0f} ({zone}) at price ${current_price:.2f}"


# Registry mapping rule types to evaluators
EVALUATORS: Dict[RuleType, ConditionEvaluator] = {
    RuleType.PRICE_BELOW_COST_PCT: PriceBelowCostPctEvaluator(),
    RuleType.PRICE_ABOVE_COST_PCT: PriceAboveCostPctEvaluator(),
    RuleType.PRICE_BELOW_VALUE: PriceBelowValueEvaluator(),
    RuleType.PRICE_ABOVE_VALUE: PriceAboveValueEvaluator(),
    RuleType.RSI_BELOW_VALUE: RSIBelowValueEvaluator(),
    RuleType.RSI_ABOVE_VALUE: RSIAboveValueEvaluator(),
}


def get_evaluator(rule_type: RuleType) -> Optional[ConditionEvaluator]:
    """Get evaluator for a rule type."""
    return EVALUATORS.get(rule_type)
