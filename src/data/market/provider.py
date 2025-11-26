"""Market data provider using yfinance with caching."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import yfinance as yf
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db.models import PriceCache

logger = logging.getLogger(__name__)
settings = get_settings()


class MarketDataProvider:
    """Market data provider with database-backed caching."""

    def __init__(self, cache_seconds: Optional[int] = None):
        """Initialize provider.

        Args:
            cache_seconds: How long to cache prices. Defaults to settings value.
        """
        self.cache_seconds = cache_seconds or settings.price_cache_seconds

    def get_price(self, symbol: str, db: Session) -> Optional[float]:
        """Get current price for a symbol.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            db: Database session

        Returns:
            Current price or None if unavailable
        """
        symbol = symbol.upper()
        now = datetime.utcnow()

        # Check cache first
        cached = db.query(PriceCache).filter_by(symbol=symbol).first()
        if cached and cached.fetched_at > now - timedelta(seconds=self.cache_seconds):
            logger.debug(f"Cache hit for {symbol}: ${cached.price}")
            return cached.price

        # Fetch from yfinance with fallback
        try:
            ticker = yf.Ticker(symbol)
            price = ticker.info.get("currentPrice") or ticker.info.get(
                "regularMarketPrice"
            )

            # Fallback: use last close from history
            if price is None:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])

            if price is None:
                logger.warning(f"Could not fetch price for {symbol}")
                return None

            # Update cache
            if cached:
                cached.price = price
                cached.fetched_at = now
            else:
                db.add(PriceCache(symbol=symbol, price=price, fetched_at=now))

            logger.debug(f"Fetched {symbol}: ${price}")
            return price

        except Exception as e:
            logger.error(f"yfinance error for {symbol}: {e}")
            return None

    def get_prices(self, symbols: list[str], db: Session) -> dict[str, float]:
        """Get prices for multiple symbols.

        Args:
            symbols: List of stock ticker symbols
            db: Database session

        Returns:
            Dict of symbol -> price (only includes successful fetches)
        """
        prices = {}
        for symbol in symbols:
            price = self.get_price(symbol, db)
            if price is not None:
                prices[symbol.upper()] = price
        return prices


# Singleton instance for convenience
market_data = MarketDataProvider()
