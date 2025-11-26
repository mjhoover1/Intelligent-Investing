"""Pydantic schemas for rule operations."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class RuleType(str, Enum):
    """Supported rule condition types."""

    # Price-based rules
    PRICE_BELOW_COST_PCT = "price_below_cost_pct"
    PRICE_ABOVE_COST_PCT = "price_above_cost_pct"
    PRICE_BELOW_VALUE = "price_below_value"
    PRICE_ABOVE_VALUE = "price_above_value"

    # RSI indicator rules
    RSI_BELOW_VALUE = "rsi_below_value"  # Oversold signal (e.g., RSI < 30)
    RSI_ABOVE_VALUE = "rsi_above_value"  # Overbought signal (e.g., RSI > 70)

    def description(self) -> str:
        """Human-readable description of the rule type."""
        descriptions = {
            self.PRICE_BELOW_COST_PCT: "Alert if price drops X% below cost basis",
            self.PRICE_ABOVE_COST_PCT: "Alert if price rises X% above cost basis",
            self.PRICE_BELOW_VALUE: "Alert if price drops below $X",
            self.PRICE_ABOVE_VALUE: "Alert if price rises above $X",
            self.RSI_BELOW_VALUE: "Alert if RSI drops below X (oversold signal)",
            self.RSI_ABOVE_VALUE: "Alert if RSI rises above X (overbought signal)",
        }
        return descriptions.get(self, "Unknown rule type")

    @property
    def is_indicator_rule(self) -> bool:
        """Check if this rule type requires indicator data."""
        return self in (self.RSI_BELOW_VALUE, self.RSI_ABOVE_VALUE)

    @property
    def indicator_type(self) -> Optional[str]:
        """Get the indicator type for this rule, if applicable."""
        if self in (self.RSI_BELOW_VALUE, self.RSI_ABOVE_VALUE):
            return "rsi"
        return None


class RuleCreate(BaseModel):
    """Schema for creating a new rule."""

    name: str = Field(..., min_length=1, max_length=100)
    rule_type: RuleType
    threshold: float = Field(..., description="Can be negative for percentage rules (e.g., -10 means 10% below cost)")
    symbol: Optional[str] = Field(None, max_length=10, description="NULL = apply to all holdings")
    enabled: bool = True
    cooldown_minutes: int = Field(60, ge=0)

    @model_validator(mode="after")
    def validate_threshold_for_rule_type(self) -> "RuleCreate":
        """Validate threshold based on rule type."""
        rule_type = self.rule_type
        threshold = self.threshold

        # RSI rules: threshold must be between 0 and 100
        if rule_type in (RuleType.RSI_BELOW_VALUE, RuleType.RSI_ABOVE_VALUE):
            if threshold < 0 or threshold > 100:
                raise ValueError(f"RSI threshold must be between 0 and 100, got {threshold}")

        # Absolute price rules: threshold must be positive
        if rule_type in (RuleType.PRICE_BELOW_VALUE, RuleType.PRICE_ABOVE_VALUE):
            if threshold <= 0:
                raise ValueError(f"Absolute price threshold must be positive, got {threshold}")

        return self


class RuleUpdate(BaseModel):
    """Schema for updating a rule."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    threshold: Optional[float] = None
    symbol: Optional[str] = None
    enabled: Optional[bool] = None
    cooldown_minutes: Optional[int] = Field(None, ge=0)


class RuleResponse(BaseModel):
    """Schema for rule response."""

    id: str
    user_id: str
    name: str
    rule_type: RuleType
    threshold: float
    symbol: Optional[str]
    enabled: bool
    cooldown_minutes: int
    last_triggered_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class EvaluationResult(BaseModel):
    """Result of evaluating a rule against a holding."""

    rule_id: str
    rule_name: str
    rule_type: RuleType
    symbol: str
    triggered: bool
    reason: str
    current_price: float
    cost_basis: Optional[float] = None
    threshold: float
    holding_id: Optional[str] = None
    indicator_value: Optional[float] = None  # For indicator-based rules
