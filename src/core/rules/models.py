"""Pydantic schemas for rule operations."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RuleType(str, Enum):
    """Supported rule condition types."""

    PRICE_BELOW_COST_PCT = "price_below_cost_pct"
    PRICE_ABOVE_COST_PCT = "price_above_cost_pct"
    PRICE_BELOW_VALUE = "price_below_value"
    PRICE_ABOVE_VALUE = "price_above_value"

    def description(self) -> str:
        """Human-readable description of the rule type."""
        descriptions = {
            self.PRICE_BELOW_COST_PCT: "Alert if price drops X% below cost basis",
            self.PRICE_ABOVE_COST_PCT: "Alert if price rises X% above cost basis",
            self.PRICE_BELOW_VALUE: "Alert if price drops below $X",
            self.PRICE_ABOVE_VALUE: "Alert if price rises above $X",
        }
        return descriptions.get(self, "Unknown rule type")


class RuleCreate(BaseModel):
    """Schema for creating a new rule."""

    name: str = Field(..., min_length=1, max_length=100)
    rule_type: RuleType
    threshold: float = Field(..., gt=0)
    symbol: Optional[str] = Field(None, max_length=10, description="NULL = apply to all holdings")
    enabled: bool = True
    cooldown_minutes: int = Field(60, ge=0)


class RuleUpdate(BaseModel):
    """Schema for updating a rule."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    threshold: Optional[float] = Field(None, gt=0)
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
