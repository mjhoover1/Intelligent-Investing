"""Market data provider using yfinance with caching."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db.models import IndicatorCache, MarketDataCache, PriceCache

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

    def get_rsi(
        self,
        symbol: str,
        db: Session,
        period: int = 14,
        timeframe: str = "1d",
    ) -> Optional[float]:
        """Get RSI (Relative Strength Index) for a symbol.

        Args:
            symbol: Stock ticker symbol
            db: Database session
            period: RSI period (default 14)
            timeframe: Timeframe for calculation (default "1d")

        Returns:
            RSI value (0-100) or None if unavailable
        """
        symbol = symbol.upper()
        indicator_type = f"rsi_{period}"
        now = datetime.utcnow()

        # Check cache first
        cached = (
            db.query(IndicatorCache)
            .filter_by(symbol=symbol, indicator_type=indicator_type, timeframe=timeframe)
            .first()
        )
        if cached and cached.fetched_at > now - timedelta(seconds=self.cache_seconds):
            logger.debug(f"Cache hit for {symbol} RSI: {cached.value}")
            return cached.value

        # Fetch historical data and calculate RSI
        try:
            ticker = yf.Ticker(symbol)
            # Need enough history to calculate RSI (period + buffer)
            hist = ticker.history(period="1mo", interval=timeframe)

            if hist.empty or len(hist) < period + 1:
                logger.warning(f"Insufficient data for {symbol} RSI calculation")
                return None

            # Calculate RSI
            rsi_value = self._calculate_rsi(hist["Close"], period)

            if rsi_value is None:
                return None

            # Update or insert cache
            if cached:
                cached.value = rsi_value
                cached.fetched_at = now
            else:
                db.add(
                    IndicatorCache(
                        symbol=symbol,
                        indicator_type=indicator_type,
                        timeframe=timeframe,
                        value=rsi_value,
                        fetched_at=now,
                    )
                )

            logger.debug(f"Calculated {symbol} RSI: {rsi_value:.2f}")
            return rsi_value

        except Exception as e:
            logger.error(f"Error calculating RSI for {symbol}: {e}")
            return None

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> Optional[float]:
        """Calculate RSI from a price series.

        Args:
            prices: Series of closing prices
            period: RSI period

        Returns:
            RSI value or None
        """
        if len(prices) < period + 1:
            return None

        # Calculate price changes
        delta = prices.diff()

        # Separate gains and losses
        gains = delta.where(delta > 0, 0.0)
        losses = (-delta).where(delta < 0, 0.0)

        # Calculate exponential moving averages
        avg_gain = gains.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = losses.ewm(com=period - 1, min_periods=period).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Return the most recent RSI value
        return float(rsi.iloc[-1])

    def get_52_week_data(
        self, symbol: str, db: Session
    ) -> Optional[Tuple[float, float]]:
        """Get 52-week high and low for a symbol.

        Args:
            symbol: Stock ticker symbol
            db: Database session

        Returns:
            Tuple of (high_52_week, low_52_week) or None if unavailable
        """
        symbol = symbol.upper()
        now = datetime.utcnow()

        # Check cache first (use longer TTL for 52-week data)
        cached = db.query(MarketDataCache).filter_by(symbol=symbol).first()
        # Cache 52-week data for 4 hours
        cache_ttl = max(self.cache_seconds, 4 * 3600)
        if cached and cached.fetched_at > now - timedelta(seconds=cache_ttl):
            if cached.high_52_week is not None and cached.low_52_week is not None:
                logger.debug(
                    f"Cache hit for {symbol} 52wk: H={cached.high_52_week}, L={cached.low_52_week}"
                )
                return (cached.high_52_week, cached.low_52_week)

        # Fetch from yfinance
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            high_52 = info.get("fiftyTwoWeekHigh")
            low_52 = info.get("fiftyTwoWeekLow")

            if high_52 is None or low_52 is None:
                logger.warning(f"52-week data unavailable for {symbol}")
                return None

            # Update or insert cache
            if cached:
                cached.high_52_week = high_52
                cached.low_52_week = low_52
                cached.fetched_at = now
            else:
                db.add(
                    MarketDataCache(
                        symbol=symbol,
                        high_52_week=high_52,
                        low_52_week=low_52,
                        fetched_at=now,
                    )
                )

            logger.debug(f"Fetched {symbol} 52wk: H={high_52}, L={low_52}")
            return (high_52, low_52)

        except Exception as e:
            logger.error(f"Error fetching 52-week data for {symbol}: {e}")
            return None

    def get_indicator(
        self,
        symbol: str,
        indicator_type: str,
        db: Session,
        timeframe: str = "1d",
    ) -> Optional[float]:
        """Get a technical indicator value for a symbol.

        Args:
            symbol: Stock ticker symbol
            indicator_type: Type of indicator ('rsi', 'rsi_14', etc.)
            db: Database session
            timeframe: Timeframe for calculation

        Returns:
            Indicator value or None if unavailable
        """
        # Normalize indicator type
        indicator_type = indicator_type.lower()

        if indicator_type == "rsi" or indicator_type == "rsi_14":
            return self.get_rsi(symbol, db, period=14, timeframe=timeframe)
        elif indicator_type.startswith("rsi_"):
            try:
                period = int(indicator_type.split("_")[1])
                return self.get_rsi(symbol, db, period=period, timeframe=timeframe)
            except (IndexError, ValueError):
                logger.warning(f"Invalid RSI indicator type: {indicator_type}")
                return None
        else:
            logger.warning(f"Unknown indicator type: {indicator_type}")
            return None


# Singleton instance for convenience
market_data = MarketDataProvider()
