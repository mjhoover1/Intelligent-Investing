"""Metrics and analytics API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_current_user
from src.core.metrics import MetricsService
from src.db.models import User

router = APIRouter(prefix="/metrics", tags=["metrics"])


# Response Models

class FeedbackBreakdownResponse(BaseModel):
    """Feedback breakdown response."""

    total: int
    useful: int
    noise: int
    actionable: int
    unrated: int
    usefulness_rate: Optional[float]
    noise_rate: Optional[float]
    rating_rate: float


class PriceMovementResponse(BaseModel):
    """Price movement statistics response."""

    avg_3d_change_pct: Optional[float]
    avg_7d_change_pct: Optional[float]
    avg_30d_change_pct: Optional[float]
    positive_3d_rate: Optional[float]
    positive_7d_rate: Optional[float]
    positive_30d_rate: Optional[float]


class RuleMetricsResponse(BaseModel):
    """Rule metrics response."""

    rule_id: str
    rule_name: str
    rule_type: str
    symbol: Optional[str]
    enabled: bool
    total_alerts: int
    alerts_last_7d: int
    alerts_last_30d: int
    feedback: FeedbackBreakdownResponse
    price_movement: PriceMovementResponse
    last_fired_at: Optional[datetime]
    avg_fires_per_week: float


class AssetMetricsResponse(BaseModel):
    """Asset metrics response."""

    symbol: str
    total_alerts: int
    alerts_last_7d: int
    alerts_last_30d: int
    feedback: FeedbackBreakdownResponse
    price_movement: PriceMovementResponse
    alerts_by_rule_type: Dict[str, int]
    best_rule_id: Optional[str]
    best_rule_usefulness: Optional[float]


class UserMetricsResponse(BaseModel):
    """User metrics response."""

    user_id: str
    total_holdings: int
    total_rules: int
    active_rules: int
    total_alerts: int
    alerts_last_7d: int
    alerts_last_30d: int
    feedback: FeedbackBreakdownResponse
    feedback_rate: float
    most_active_rule: Optional[str]
    most_active_symbol: Optional[str]
    best_performing_rule: Optional[str]
    noisiest_rule: Optional[str]


class MetricsSummaryResponse(BaseModel):
    """Overall metrics summary response."""

    period_days: int
    generated_at: datetime
    user_metrics: Optional[UserMetricsResponse]
    rule_metrics: List[RuleMetricsResponse]
    asset_metrics: List[AssetMetricsResponse]
    total_alerts_in_period: int
    overall_usefulness_rate: Optional[float]
    most_useful_rule: Optional[str]
    noisiest_rule: Optional[str]
    most_signals_asset: Optional[str]


# Helper functions

def _feedback_to_response(feedback) -> FeedbackBreakdownResponse:
    """Convert FeedbackBreakdown to response model."""
    return FeedbackBreakdownResponse(
        total=feedback.total,
        useful=feedback.useful,
        noise=feedback.noise,
        actionable=feedback.actionable,
        unrated=feedback.unrated,
        usefulness_rate=feedback.usefulness_rate,
        noise_rate=feedback.noise_rate,
        rating_rate=feedback.rating_rate,
    )


def _price_movement_to_response(movement) -> PriceMovementResponse:
    """Convert PriceMovement to response model."""
    return PriceMovementResponse(
        avg_3d_change_pct=movement.avg_3d_change_pct,
        avg_7d_change_pct=movement.avg_7d_change_pct,
        avg_30d_change_pct=movement.avg_30d_change_pct,
        positive_3d_rate=movement.positive_3d_rate,
        positive_7d_rate=movement.positive_7d_rate,
        positive_30d_rate=movement.positive_30d_rate,
    )


def _rule_metrics_to_response(metrics) -> RuleMetricsResponse:
    """Convert RuleMetrics to response model."""
    return RuleMetricsResponse(
        rule_id=metrics.rule_id,
        rule_name=metrics.rule_name,
        rule_type=metrics.rule_type,
        symbol=metrics.symbol,
        enabled=metrics.enabled,
        total_alerts=metrics.total_alerts,
        alerts_last_7d=metrics.alerts_last_7d,
        alerts_last_30d=metrics.alerts_last_30d,
        feedback=_feedback_to_response(metrics.feedback),
        price_movement=_price_movement_to_response(metrics.price_movement),
        last_fired_at=metrics.last_fired_at,
        avg_fires_per_week=metrics.avg_fires_per_week,
    )


def _asset_metrics_to_response(metrics) -> AssetMetricsResponse:
    """Convert AssetMetrics to response model."""
    return AssetMetricsResponse(
        symbol=metrics.symbol,
        total_alerts=metrics.total_alerts,
        alerts_last_7d=metrics.alerts_last_7d,
        alerts_last_30d=metrics.alerts_last_30d,
        feedback=_feedback_to_response(metrics.feedback),
        price_movement=_price_movement_to_response(metrics.price_movement),
        alerts_by_rule_type=metrics.alerts_by_rule_type,
        best_rule_id=metrics.best_rule_id,
        best_rule_usefulness=metrics.best_rule_usefulness,
    )


def _user_metrics_to_response(metrics) -> UserMetricsResponse:
    """Convert UserMetrics to response model."""
    return UserMetricsResponse(
        user_id=metrics.user_id,
        total_holdings=metrics.total_holdings,
        total_rules=metrics.total_rules,
        active_rules=metrics.active_rules,
        total_alerts=metrics.total_alerts,
        alerts_last_7d=metrics.alerts_last_7d,
        alerts_last_30d=metrics.alerts_last_30d,
        feedback=_feedback_to_response(metrics.feedback),
        feedback_rate=metrics.feedback_rate,
        most_active_rule=metrics.most_active_rule,
        most_active_symbol=metrics.most_active_symbol,
        best_performing_rule=metrics.best_performing_rule,
        noisiest_rule=metrics.noisiest_rule,
    )


# Routes

@router.get("/summary", response_model=MetricsSummaryResponse)
def get_metrics_summary(
    period_days: int = Query(30, ge=1, le=365, description="Period in days for metrics"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get complete metrics summary for the authenticated user.

    Includes:
    - User engagement metrics
    - Per-rule performance statistics
    - Per-asset signal statistics
    - Highlights and insights
    """
    service = MetricsService(db)
    summary = service.get_summary(user.id, period_days)

    return MetricsSummaryResponse(
        period_days=summary.period_days,
        generated_at=summary.generated_at,
        user_metrics=(
            _user_metrics_to_response(summary.user_metrics)
            if summary.user_metrics else None
        ),
        rule_metrics=[_rule_metrics_to_response(r) for r in summary.rule_metrics],
        asset_metrics=[_asset_metrics_to_response(a) for a in summary.asset_metrics],
        total_alerts_in_period=summary.total_alerts_in_period,
        overall_usefulness_rate=summary.overall_usefulness_rate,
        most_useful_rule=summary.most_useful_rule,
        noisiest_rule=summary.noisiest_rule,
        most_signals_asset=summary.most_signals_asset,
    )


@router.get("/user", response_model=UserMetricsResponse)
def get_user_metrics(
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get aggregate metrics for the authenticated user."""
    service = MetricsService(db)
    metrics = service.get_user_metrics(user.id, period_days)
    return _user_metrics_to_response(metrics)


@router.get("/rules", response_model=List[RuleMetricsResponse])
def get_rule_metrics(
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get metrics for all rules belonging to the authenticated user.

    Results are sorted by total alerts (descending).
    """
    service = MetricsService(db)
    metrics_list = service.get_rule_metrics(user.id, period_days)
    return [_rule_metrics_to_response(m) for m in metrics_list]


@router.get("/rules/{rule_id}", response_model=RuleMetricsResponse)
def get_rule_performance(
    rule_id: str,
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get detailed performance report for a specific rule.

    Example response interpretation:
    - "RSI oversold signals had 67% usefulness rating over last 30 days"
    - "Average 3-day price change after alert: +2.3%"
    """
    from fastapi import HTTPException, status

    service = MetricsService(db)
    metrics = service.get_rule_performance_report(user.id, rule_id, period_days)

    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    return _rule_metrics_to_response(metrics)


@router.get("/assets", response_model=List[AssetMetricsResponse])
def get_asset_metrics(
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get metrics for all assets with alerts.

    Results are sorted by total alerts (descending).
    """
    service = MetricsService(db)
    metrics_list = service.get_asset_metrics(user.id, period_days)
    return [_asset_metrics_to_response(m) for m in metrics_list]


@router.get("/assets/{symbol}", response_model=AssetMetricsResponse)
def get_asset_performance(
    symbol: str,
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get detailed performance report for a specific asset.

    Example response interpretation:
    - "AUR had 15 signals in the last 30 days"
    - "RSI rules performed best with 75% usefulness"
    - "Average 7-day price movement after alert: +3.5%"
    """
    from fastapi import HTTPException, status

    service = MetricsService(db)
    metrics = service.get_asset_performance_report(user.id, symbol, period_days)

    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No alerts found for symbol {symbol.upper()}",
        )

    return _asset_metrics_to_response(metrics)


@router.get("/leaderboard/rules")
def get_rules_leaderboard(
    period_days: int = Query(30, ge=1, le=365),
    min_ratings: int = Query(3, ge=1, description="Minimum ratings to include"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a leaderboard of rules by usefulness.

    Only includes rules with at least `min_ratings` rated alerts.
    """
    service = MetricsService(db)
    metrics_list = service.get_rule_metrics(user.id, period_days)

    # Filter to rules with enough ratings
    qualified = [
        m for m in metrics_list
        if m.feedback.rated_count >= min_ratings
    ]

    # Sort by usefulness rate descending
    qualified.sort(
        key=lambda m: m.feedback.usefulness_rate or 0,
        reverse=True
    )

    return [
        {
            "rank": i + 1,
            "rule_id": m.rule_id,
            "rule_name": m.rule_name,
            "rule_type": m.rule_type,
            "total_alerts": m.total_alerts,
            "rated_alerts": m.feedback.rated_count,
            "usefulness_rate": round(m.feedback.usefulness_rate or 0, 1),
            "noise_rate": round(m.feedback.noise_rate or 0, 1),
        }
        for i, m in enumerate(qualified)
    ]


@router.get("/leaderboard/assets")
def get_assets_leaderboard(
    period_days: int = Query(30, ge=1, le=365),
    min_ratings: int = Query(2, ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a leaderboard of assets by signal usefulness.

    Only includes assets with at least `min_ratings` rated alerts.
    """
    service = MetricsService(db)
    metrics_list = service.get_asset_metrics(user.id, period_days)

    # Filter to assets with enough ratings
    qualified = [
        m for m in metrics_list
        if m.feedback.rated_count >= min_ratings
    ]

    # Sort by usefulness rate descending
    qualified.sort(
        key=lambda m: m.feedback.usefulness_rate or 0,
        reverse=True
    )

    return [
        {
            "rank": i + 1,
            "symbol": m.symbol,
            "total_alerts": m.total_alerts,
            "rated_alerts": m.feedback.rated_count,
            "usefulness_rate": round(m.feedback.usefulness_rate or 0, 1),
            "avg_7d_change": round(m.price_movement.avg_7d_change_pct or 0, 2),
        }
        for i, m in enumerate(qualified)
    ]
