"""Market data Pydantic models."""

from datetime import datetime
from pydantic import BaseModel


class Price(BaseModel):
    """Current price data for a symbol."""

    symbol: str
    price: float
    fetched_at: datetime

    class Config:
        from_attributes = True
