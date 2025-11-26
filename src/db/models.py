"""SQLAlchemy ORM models."""

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    Date,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.utcnow()


class User(Base):
    """User model (stub for future SaaS)."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    # Relationships
    holdings = relationship("Holding", back_populates="user", cascade="all, delete-orphan")
    rules = relationship("Rule", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class Holding(Base):
    """Portfolio holding model."""

    __tablename__ = "holdings"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(10), nullable=False)
    shares = Column(Float, nullable=False)
    cost_basis = Column(Float, nullable=False)  # Per share
    purchase_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="holdings")
    alerts = relationship("Alert", back_populates="holding")

    @property
    def total_cost(self) -> float:
        """Total cost basis for this position."""
        return self.shares * self.cost_basis

    def __repr__(self) -> str:
        return f"<Holding(id={self.id}, symbol={self.symbol}, shares={self.shares})>"


class Rule(Base):
    """Alert rule model."""

    __tablename__ = "rules"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    rule_type = Column(String(50), nullable=False)  # e.g., 'price_below_cost_pct'
    threshold = Column(Float, nullable=False)
    symbol = Column(String(10), nullable=True)  # NULL = apply to all holdings
    enabled = Column(Boolean, default=True, nullable=False)
    cooldown_minutes = Column(Integer, default=60, nullable=False)
    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="rules")
    alerts = relationship("Alert", back_populates="rule", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Rule(id={self.id}, name={self.name}, type={self.rule_type})>"


class Alert(Base):
    """Triggered alert model."""

    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    rule_id = Column(String, ForeignKey("rules.id"), nullable=False)
    holding_id = Column(String, ForeignKey("holdings.id"), nullable=True)
    symbol = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    ai_summary = Column(Text, nullable=True)
    triggered_at = Column(DateTime, default=utcnow, nullable=False)
    notified = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="alerts")
    rule = relationship("Rule", back_populates="alerts")
    holding = relationship("Holding", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, symbol={self.symbol}, triggered_at={self.triggered_at})>"


class PriceCache(Base):
    """Market price cache model."""

    __tablename__ = "price_cache"

    symbol = Column(String(10), primary_key=True)
    price = Column(Float, nullable=False)
    fetched_at = Column(DateTime, nullable=False, default=utcnow)

    def __repr__(self) -> str:
        return f"<PriceCache(symbol={self.symbol}, price={self.price})>"


class IndicatorCache(Base):
    """Technical indicator cache model."""

    __tablename__ = "indicator_cache"

    id = Column(String, primary_key=True, default=generate_uuid)
    symbol = Column(String(10), nullable=False, index=True)
    indicator_type = Column(String(20), nullable=False)  # 'rsi', 'macd', etc.
    timeframe = Column(String(10), nullable=False, default="1d")  # '1d', '1h', etc.
    value = Column(Float, nullable=False)
    fetched_at = Column(DateTime, nullable=False, default=utcnow)

    def __repr__(self) -> str:
        return f"<IndicatorCache(symbol={self.symbol}, type={self.indicator_type}, value={self.value})>"


class MarketDataCache(Base):
    """Extended market data cache (52-week high/low, etc.)."""

    __tablename__ = "market_data_cache"

    symbol = Column(String(10), primary_key=True)
    high_52_week = Column(Float, nullable=True)
    low_52_week = Column(Float, nullable=True)
    fetched_at = Column(DateTime, nullable=False, default=utcnow)

    def __repr__(self) -> str:
        return f"<MarketDataCache(symbol={self.symbol}, 52wk_high={self.high_52_week})>"


class NotificationSettings(Base):
    """User notification settings."""

    __tablename__ = "notification_settings"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)

    # Telegram settings
    telegram_enabled = Column(Boolean, default=False, nullable=False)
    telegram_chat_id = Column(String(50), nullable=True)

    # Console settings (for development)
    console_enabled = Column(Boolean, default=True, nullable=False)

    # Future: email, SMS, etc.
    # email_enabled = Column(Boolean, default=False, nullable=False)
    # email_address = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<NotificationSettings(user_id={self.user_id}, telegram={self.telegram_enabled})>"
