"""Pydantic schemas for portfolio operations."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class HoldingCreate(BaseModel):
    """Schema for creating a new holding."""

    symbol: str = Field(..., min_length=1, max_length=10)
    shares: float = Field(..., gt=0)
    cost_basis: float = Field(..., gt=0, description="Cost basis per share")
    purchase_date: Optional[date] = None

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.upper().strip()


class HoldingUpdate(BaseModel):
    """Schema for updating a holding."""

    shares: Optional[float] = Field(None, gt=0)
    cost_basis: Optional[float] = Field(None, gt=0)
    purchase_date: Optional[date] = None


class HoldingResponse(BaseModel):
    """Schema for holding response."""

    id: str
    user_id: str
    symbol: str
    shares: float
    cost_basis: float
    purchase_date: Optional[date]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HoldingWithPrice(HoldingResponse):
    """Holding response with current market data."""

    current_price: Optional[float] = None
    current_value: Optional[float] = None
    total_cost: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None


class PortfolioSummary(BaseModel):
    """Portfolio summary with aggregated metrics."""

    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    holdings_count: int
