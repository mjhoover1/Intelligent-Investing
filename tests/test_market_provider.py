"""Tests for market data provider."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.data.market.provider import MarketDataProvider
from src.db.models import PriceCache


class TestMarketDataProvider:
    """Tests for MarketDataProvider."""

    def test_returns_cached_price_when_fresh(self):
        """Should return cached price without hitting yfinance."""
        mock_db = MagicMock()

        # Create a fresh cache entry
        cached_price = PriceCache(
            symbol="AAPL",
            price=150.0,
            fetched_at=datetime.utcnow(),  # Fresh
        )
        mock_db.query.return_value.filter_by.return_value.first.return_value = cached_price

        provider = MarketDataProvider(cache_seconds=60)

        # Should return cached price
        price = provider.get_price("AAPL", mock_db)

        assert price == 150.0

    def test_fetches_from_yfinance_when_cache_stale(self):
        """Should fetch from yfinance when cache is stale."""
        mock_db = MagicMock()

        # Create a stale cache entry
        stale_time = datetime.utcnow() - timedelta(seconds=120)
        cached_price = MagicMock()
        cached_price.price = 150.0
        cached_price.fetched_at = stale_time
        mock_db.query.return_value.filter_by.return_value.first.return_value = cached_price

        provider = MarketDataProvider(cache_seconds=60)

        # Mock yfinance Ticker
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 155.0}

        with patch('src.data.market.provider.yf.Ticker', return_value=mock_ticker):
            price = provider.get_price("AAPL", mock_db)
            assert price == 155.0

    def test_fetches_from_yfinance_when_no_cache(self):
        """Should fetch from yfinance when no cache exists."""
        mock_db = MagicMock()

        # No cache entry
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        provider = MarketDataProvider(cache_seconds=60)

        # Mock yfinance Ticker
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 160.0}

        with patch('src.data.market.provider.yf.Ticker', return_value=mock_ticker):
            price = provider.get_price("AAPL", mock_db)
            assert price == 160.0

    def test_cache_prevents_second_yfinance_call(self):
        """Cache should prevent redundant yfinance calls."""
        mock_db = MagicMock()

        # First call: no cache
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        provider = MarketDataProvider(cache_seconds=60)

        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 150.0}

        with patch('src.data.market.provider.yf.Ticker', return_value=mock_ticker) as mock_yf:
            # First call - should fetch
            provider.get_price("AAPL", mock_db)
            assert mock_yf.call_count == 1

            # Simulate fresh cache for second call
            fresh_cache = MagicMock()
            fresh_cache.price = 150.0
            fresh_cache.fetched_at = datetime.utcnow()
            mock_db.query.return_value.filter_by.return_value.first.return_value = fresh_cache

            # Second call - should use cache
            price = provider.get_price("AAPL", mock_db)
            assert price == 150.0
            # yfinance should NOT have been called again
            assert mock_yf.call_count == 1
