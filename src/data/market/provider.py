"""Market data provider using yfinance with caching."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple


def _utcnow() -> datetime:
    """Get current UTC time as naive datetime for database compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db.models import IndicatorCache, MarketDataCache, PriceCache

logger = logging.getLogger(__name__)
settings = get_settings()

# Timeout for yfinance API calls (seconds)
YFINANCE_TIMEOUT = 30

# Symbol format mappings for Yahoo Finance compatibility
# Maps user-friendly formats to Yahoo Finance formats
SYMBOL_MAPPINGS = {
    # Warrant formats: /WS -> -WT (Yahoo Finance warrant suffix)
    "/WS": "-WT",
    "/W": "-WT",
    ".WS": "-WT",
    ".W": "-WT",
}


def normalize_symbol(symbol: str) -> tuple[str, str]:
    """Normalize a symbol to Yahoo Finance format.

    Args:
        symbol: Original symbol (e.g., 'IONQ/WS')

    Returns:
        Tuple of (yahoo_symbol, original_symbol)
    """
    original = symbol.upper()
    yahoo_symbol = original

    # Check for known suffix mappings
    for suffix, yahoo_suffix in SYMBOL_MAPPINGS.items():
        if original.endswith(suffix.upper()):
            base = original[: -len(suffix)]
            yahoo_symbol = base + yahoo_suffix
            logger.debug(f"Normalized symbol {original} -> {yahoo_symbol}")
            break

    return yahoo_symbol, original


class MarketDataProvider:
    """Market data provider with database-backed caching."""

    # Shared executor for timeout handling (reused across calls)
    _executor: Optional[ThreadPoolExecutor] = None

    def __init__(self, cache_seconds: Optional[int] = None, timeout: int = YFINANCE_TIMEOUT):
        """Initialize provider.

        Args:
            cache_seconds: How long to cache prices. Defaults to settings value.
            timeout: Timeout for yfinance API calls in seconds.
        """
        self.cache_seconds = cache_seconds or settings.price_cache_seconds
        self.timeout = timeout

    @classmethod
    def _get_executor(cls) -> ThreadPoolExecutor:
        """Get or create shared executor."""
        if cls._executor is None:
            cls._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="market_data")
        return cls._executor

    def _fetch_with_timeout(self, func, *args, **kwargs):
        """Execute a function with timeout protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result or None on timeout
        """
        executor = self._get_executor()
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=self.timeout)
        except FuturesTimeoutError:
            logger.warning(f"Timeout after {self.timeout}s fetching market data")
            return None

    def get_price(self, symbol: str, db: Session) -> Optional[float]:
        """Get current price for a symbol.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', 'IONQ/WS')
            db: Database session

        Returns:
            Current price or None if unavailable
        """
        # Normalize symbol for Yahoo Finance (e.g., IONQ/WS -> IONQ-WT)
        yahoo_symbol, original_symbol = normalize_symbol(symbol)
        now = _utcnow()

        # Check cache first (use original symbol for cache key)
        cached = db.query(PriceCache).filter_by(symbol=original_symbol).first()
        if cached and cached.fetched_at >= now - timedelta(seconds=self.cache_seconds):
            logger.debug(f"Cache hit for {original_symbol}: ${cached.price}")
            return cached.price

        # Fetch from yfinance with fallback (use Yahoo symbol)
        def _fetch_price():
            ticker = yf.Ticker(yahoo_symbol)
            p = ticker.info.get("currentPrice") or ticker.info.get("regularMarketPrice")
            if p is None:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    p = float(hist["Close"].iloc[-1])
            return p

        try:
            price = self._fetch_with_timeout(_fetch_price)
            if price is None:
                # Timeout or no data
                logger.warning(f"Could not fetch price for {original_symbol} (Yahoo: {yahoo_symbol})")
                return None

            # Update cache using merge for upsert (avoids race condition)
            db.merge(PriceCache(symbol=original_symbol, price=price, fetched_at=now))
            db.flush()

            logger.debug(f"Fetched {original_symbol}: ${price}")
            return price

        except Exception as e:
            logger.error(f"yfinance error for {original_symbol}: {e}")
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
        # Normalize symbol for Yahoo Finance (e.g., IONQ/WS -> IONQ-WT)
        yahoo_symbol, original_symbol = normalize_symbol(symbol)
        indicator_type = f"rsi_{period}"
        now = _utcnow()

        # Check cache first (use original_symbol for cache key)
        cached = (
            db.query(IndicatorCache)
            .filter_by(symbol=original_symbol, indicator_type=indicator_type, timeframe=timeframe)
            .first()
        )
        if cached and cached.fetched_at >= now - timedelta(seconds=self.cache_seconds):
            logger.debug(f"Cache hit for {original_symbol} RSI: {cached.value}")
            return cached.value

        # Fetch historical data and calculate RSI (use yahoo_symbol for API)
        def _fetch_rsi_data():
            ticker = yf.Ticker(yahoo_symbol)
            return ticker.history(period="1mo", interval=timeframe)

        try:
            hist = self._fetch_with_timeout(_fetch_rsi_data)

            if hist is None or hist.empty or len(hist) < period + 1:
                logger.warning(f"Insufficient data for {original_symbol} (Yahoo: {yahoo_symbol}) RSI calculation")
                return None

            # Calculate RSI
            rsi_value = self._calculate_rsi(hist["Close"], period)

            if rsi_value is None:
                return None

            # Update or insert cache (handle race condition)
            if cached:
                cached.value = rsi_value
                cached.fetched_at = now
                db.flush()
            else:
                # Try insert, handle race condition where another process inserted
                from sqlalchemy.exc import IntegrityError
                try:
                    db.add(
                        IndicatorCache(
                            symbol=original_symbol,
                            indicator_type=indicator_type,
                            timeframe=timeframe,
                            value=rsi_value,
                            fetched_at=now,
                        )
                    )
                    db.flush()
                except IntegrityError:
                    # Another process inserted - rollback and update instead
                    db.rollback()
                    cached = (
                        db.query(IndicatorCache)
                        .filter_by(symbol=original_symbol, indicator_type=indicator_type, timeframe=timeframe)
                        .first()
                    )
                    if cached:
                        cached.value = rsi_value
                        cached.fetched_at = now
                        db.flush()

            logger.debug(f"Calculated {original_symbol} RSI: {rsi_value:.2f}")
            return rsi_value

        except Exception as e:
            logger.error(f"Error calculating RSI for {original_symbol}: {e}")
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

        # Get the most recent values
        last_avg_gain = avg_gain.iloc[-1]
        last_avg_loss = avg_loss.iloc[-1]

        # Handle edge cases to avoid division by zero and NaN
        if pd.isna(last_avg_gain) or pd.isna(last_avg_loss):
            return None
        if last_avg_loss == 0:
            # All gains, no losses - RSI is 100 (extremely overbought)
            return 100.0 if last_avg_gain > 0 else 50.0  # No movement = neutral

        # Calculate RS and RSI
        rs = last_avg_gain / last_avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Return the RSI value, clamped to valid range
        return float(max(0, min(100, rsi)))

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
        now = _utcnow()

        # Check cache first (use longer TTL for 52-week data)
        cached = db.query(MarketDataCache).filter_by(symbol=symbol).first()
        # Cache 52-week data for 4 hours
        cache_ttl = max(self.cache_seconds, 4 * 3600)
        if cached and cached.fetched_at >= now - timedelta(seconds=cache_ttl):
            if cached.high_52_week is not None and cached.low_52_week is not None:
                logger.debug(
                    f"Cache hit for {symbol} 52wk: H={cached.high_52_week}, L={cached.low_52_week}"
                )
                return (cached.high_52_week, cached.low_52_week)

        # Fetch from yfinance
        def _fetch_52_week():
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return info.get("fiftyTwoWeekHigh"), info.get("fiftyTwoWeekLow")

        try:
            result = self._fetch_with_timeout(_fetch_52_week)
            if result is None:
                logger.warning(f"Timeout fetching 52-week data for {symbol}")
                return None

            high_52, low_52 = result

            if high_52 is None or low_52 is None:
                logger.warning(f"52-week data unavailable for {symbol}")
                return None

            # Update cache using merge for upsert (avoids race condition)
            db.merge(
                MarketDataCache(
                    symbol=symbol,
                    high_52_week=high_52,
                    low_52_week=low_52,
                    fetched_at=now,
                )
            )
            db.flush()

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
