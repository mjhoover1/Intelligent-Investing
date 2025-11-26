"""Pydantic schemas for alert operations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AlertCreate(BaseModel):
    """Schema for creating a new alert."""

    user_id: str
    rule_id: str
    holding_id: Optional[str] = None
    symbol: str
    message: str
    ai_summary: Optional[str] = None


class AlertResponse(BaseModel):
    """Schema for alert response."""

    id: str
    user_id: str
    rule_id: str
    holding_id: Optional[str]
    symbol: str
    message: str
    ai_summary: Optional[str]
    triggered_at: datetime
    notified: bool

    class Config:
        from_attributes = True


class AlertWithContext(AlertResponse):
    """Alert response with additional context for display."""

    rule_name: Optional[str] = None
    rule_type: Optional[str] = None
    current_price: Optional[float] = None
    cost_basis: Optional[float] = None


class AlertContextData(BaseModel):
    """Data passed to AI context generator."""

    symbol: str
    rule_name: str
    rule_type: str
    threshold: float
    current_price: float
    cost_basis: Optional[float] = None
    percent_change: Optional[float] = None
    message: str

    # Technical indicators
    rsi: Optional[float] = None
    indicator_value: Optional[float] = None  # For indicator-based rules

    # 52-week data
    high_52_week: Optional[float] = None
    low_52_week: Optional[float] = None

    @property
    def pct_from_52_week_high(self) -> Optional[float]:
        """Calculate percent below 52-week high."""
        if self.high_52_week and self.current_price:
            return ((self.current_price - self.high_52_week) / self.high_52_week) * 100
        return None

    @property
    def pct_from_52_week_low(self) -> Optional[float]:
        """Calculate percent above 52-week low."""
        if self.low_52_week and self.current_price:
            return ((self.current_price - self.low_52_week) / self.low_52_week) * 100
        return None
