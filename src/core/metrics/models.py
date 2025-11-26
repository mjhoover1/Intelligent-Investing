"""Metrics data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict


@dataclass
class FeedbackBreakdown:
    """Breakdown of alert feedback ratings."""

    total: int = 0
    useful: int = 0
    noise: int = 0
    actionable: int = 0
    unrated: int = 0

    @property
    def rated_count(self) -> int:
        """Total number of rated alerts."""
        return self.useful + self.noise + self.actionable

    @property
    def usefulness_rate(self) -> Optional[float]:
        """Percentage of rated alerts marked useful or actionable."""
        if self.rated_count == 0:
            return None
        return ((self.useful + self.actionable) / self.rated_count) * 100

    @property
    def noise_rate(self) -> Optional[float]:
        """Percentage of rated alerts marked as noise."""
        if self.rated_count == 0:
            return None
        return (self.noise / self.rated_count) * 100

    @property
    def rating_rate(self) -> float:
        """Percentage of alerts that have been rated."""
        if self.total == 0:
            return 0.0
        return (self.rated_count / self.total) * 100


@dataclass
class PriceMovement:
    """Price movement statistics after alerts."""

    avg_3d_change_pct: Optional[float] = None
    avg_7d_change_pct: Optional[float] = None
    avg_30d_change_pct: Optional[float] = None
    positive_3d_rate: Optional[float] = None  # % of alerts where price went up after 3d
    positive_7d_rate: Optional[float] = None
    positive_30d_rate: Optional[float] = None


@dataclass
class RuleMetrics:
    """Metrics for a single rule."""

    rule_id: str
    rule_name: str
    rule_type: str
    symbol: Optional[str]  # None = applies to all
    enabled: bool

    # Alert counts
    total_alerts: int = 0
    alerts_last_7d: int = 0
    alerts_last_30d: int = 0

    # Feedback breakdown
    feedback: FeedbackBreakdown = field(default_factory=FeedbackBreakdown)

    # Price movement after alerts
    price_movement: PriceMovement = field(default_factory=PriceMovement)

    # Timing
    last_fired_at: Optional[datetime] = None
    avg_fires_per_week: float = 0.0


@dataclass
class AssetMetrics:
    """Metrics for a single asset/symbol."""

    symbol: str

    # Alert counts
    total_alerts: int = 0
    alerts_last_7d: int = 0
    alerts_last_30d: int = 0

    # Feedback breakdown
    feedback: FeedbackBreakdown = field(default_factory=FeedbackBreakdown)

    # Price movement after alerts
    price_movement: PriceMovement = field(default_factory=PriceMovement)

    # Rule breakdown - how many alerts per rule type
    alerts_by_rule_type: Dict[str, int] = field(default_factory=dict)

    # Top performing rule for this asset
    best_rule_id: Optional[str] = None
    best_rule_usefulness: Optional[float] = None


@dataclass
class UserMetrics:
    """Aggregate metrics for a user."""

    user_id: str

    # Portfolio summary
    total_holdings: int = 0
    total_rules: int = 0
    active_rules: int = 0

    # Alert summary
    total_alerts: int = 0
    alerts_last_7d: int = 0
    alerts_last_30d: int = 0

    # Feedback summary
    feedback: FeedbackBreakdown = field(default_factory=FeedbackBreakdown)

    # Engagement
    feedback_rate: float = 0.0  # % of alerts user has rated

    # Top performers
    most_active_rule: Optional[str] = None
    most_active_symbol: Optional[str] = None
    best_performing_rule: Optional[str] = None
    noisiest_rule: Optional[str] = None


@dataclass
class MetricsSummary:
    """Overall metrics summary."""

    # Time range
    period_days: int = 30
    generated_at: datetime = field(default_factory=datetime.utcnow)

    # User metrics
    user_metrics: Optional[UserMetrics] = None

    # Per-rule metrics (sorted by alert count desc)
    rule_metrics: List[RuleMetrics] = field(default_factory=list)

    # Per-asset metrics (sorted by alert count desc)
    asset_metrics: List[AssetMetrics] = field(default_factory=list)

    # Highlights
    total_alerts_in_period: int = 0
    overall_usefulness_rate: Optional[float] = None
    most_useful_rule: Optional[str] = None
    noisiest_rule: Optional[str] = None
    most_signals_asset: Optional[str] = None
