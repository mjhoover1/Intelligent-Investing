"""Metrics aggregation service."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.models import Alert, Holding, Rule, User
from src.core.metrics.models import (
    AssetMetrics,
    FeedbackBreakdown,
    MetricsSummary,
    PriceMovement,
    RuleMetrics,
    UserMetrics,
)


class MetricsService:
    """Service for calculating and aggregating metrics."""

    def __init__(self, db: Session):
        self.db = db

    def get_summary(self, user_id: str, period_days: int = 30) -> MetricsSummary:
        """Get complete metrics summary for a user."""
        now = datetime.utcnow()
        period_start = now - timedelta(days=period_days)

        summary = MetricsSummary(
            period_days=period_days,
            generated_at=now,
        )

        # Get user metrics
        summary.user_metrics = self.get_user_metrics(user_id, period_days)

        # Get rule metrics
        summary.rule_metrics = self.get_rule_metrics(user_id, period_days)

        # Get asset metrics
        summary.asset_metrics = self.get_asset_metrics(user_id, period_days)

        # Calculate highlights
        alerts_in_period = (
            self.db.query(Alert)
            .filter(
                Alert.user_id == user_id,
                Alert.triggered_at >= period_start,
            )
            .count()
        )
        summary.total_alerts_in_period = alerts_in_period

        # Overall usefulness rate
        if summary.user_metrics:
            summary.overall_usefulness_rate = summary.user_metrics.feedback.usefulness_rate

        # Find best/worst performing rules
        rated_rules = [r for r in summary.rule_metrics if r.feedback.rated_count > 0]
        if rated_rules:
            best = max(rated_rules, key=lambda r: r.feedback.usefulness_rate or 0)
            worst = min(rated_rules, key=lambda r: r.feedback.usefulness_rate or 100)
            summary.most_useful_rule = best.rule_name
            summary.noisiest_rule = worst.rule_name

        # Most signals asset
        if summary.asset_metrics:
            top_asset = max(summary.asset_metrics, key=lambda a: a.total_alerts)
            summary.most_signals_asset = top_asset.symbol

        return summary

    def get_user_metrics(self, user_id: str, period_days: int = 30) -> UserMetrics:
        """Get aggregate metrics for a user."""
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        period_start = now - timedelta(days=period_days)

        metrics = UserMetrics(user_id=user_id)

        # Portfolio counts
        metrics.total_holdings = (
            self.db.query(Holding).filter(Holding.user_id == user_id).count()
        )
        metrics.total_rules = (
            self.db.query(Rule).filter(Rule.user_id == user_id).count()
        )
        metrics.active_rules = (
            self.db.query(Rule)
            .filter(Rule.user_id == user_id, Rule.enabled == True)  # noqa: E712
            .count()
        )

        # Alert counts
        metrics.total_alerts = (
            self.db.query(Alert).filter(Alert.user_id == user_id).count()
        )
        metrics.alerts_last_7d = (
            self.db.query(Alert)
            .filter(Alert.user_id == user_id, Alert.triggered_at >= week_ago)
            .count()
        )
        metrics.alerts_last_30d = (
            self.db.query(Alert)
            .filter(Alert.user_id == user_id, Alert.triggered_at >= period_start)
            .count()
        )

        # Feedback breakdown
        metrics.feedback = self._get_feedback_breakdown(user_id)
        metrics.feedback_rate = metrics.feedback.rating_rate

        # Find most active rule
        rule_counts = (
            self.db.query(Alert.rule_id, func.count(Alert.id).label("cnt"))
            .filter(Alert.user_id == user_id)
            .group_by(Alert.rule_id)
            .order_by(func.count(Alert.id).desc())
            .first()
        )
        if rule_counts:
            rule = self.db.query(Rule).filter(Rule.id == rule_counts[0]).first()
            if rule:
                metrics.most_active_rule = rule.name

        # Find most active symbol
        symbol_counts = (
            self.db.query(Alert.symbol, func.count(Alert.id).label("cnt"))
            .filter(Alert.user_id == user_id)
            .group_by(Alert.symbol)
            .order_by(func.count(Alert.id).desc())
            .first()
        )
        if symbol_counts:
            metrics.most_active_symbol = symbol_counts[0]

        # Find best performing rule (highest usefulness among rules with ratings)
        best_rule = self._find_best_performing_rule(user_id)
        if best_rule:
            metrics.best_performing_rule = best_rule

        # Find noisiest rule
        noisiest_rule = self._find_noisiest_rule(user_id)
        if noisiest_rule:
            metrics.noisiest_rule = noisiest_rule

        return metrics

    def get_rule_metrics(self, user_id: str, period_days: int = 30) -> List[RuleMetrics]:
        """Get metrics for all rules belonging to a user."""
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        period_start = now - timedelta(days=period_days)

        rules = self.db.query(Rule).filter(Rule.user_id == user_id).all()
        metrics_list = []

        for rule in rules:
            metrics = RuleMetrics(
                rule_id=rule.id,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                symbol=rule.symbol,
                enabled=rule.enabled,
            )

            # Get all alerts for this rule
            alerts = (
                self.db.query(Alert)
                .filter(Alert.rule_id == rule.id)
                .all()
            )

            metrics.total_alerts = len(alerts)

            # Count alerts in time windows
            metrics.alerts_last_7d = len([
                a for a in alerts if a.triggered_at >= week_ago
            ])
            metrics.alerts_last_30d = len([
                a for a in alerts if a.triggered_at >= period_start
            ])

            # Feedback breakdown
            metrics.feedback = self._get_feedback_breakdown_for_alerts(alerts)

            # Price movement
            metrics.price_movement = self._calculate_price_movement(alerts)

            # Timing
            if alerts:
                latest = max(alerts, key=lambda a: a.triggered_at)
                metrics.last_fired_at = latest.triggered_at

                # Calculate avg fires per week
                if len(alerts) > 1:
                    oldest = min(alerts, key=lambda a: a.triggered_at)
                    # Use total_seconds for accurate time span (not just integer days)
                    total_seconds = (latest.triggered_at - oldest.triggered_at).total_seconds()
                    days_span = max(total_seconds / 86400, 1)  # 86400 seconds per day, min 1 day
                    weeks_span = days_span / 7
                    metrics.avg_fires_per_week = len(alerts) / max(weeks_span, 1)

            metrics_list.append(metrics)

        # Sort by total alerts descending
        metrics_list.sort(key=lambda m: m.total_alerts, reverse=True)
        return metrics_list

    def get_asset_metrics(self, user_id: str, period_days: int = 30) -> List[AssetMetrics]:
        """Get metrics for all assets with alerts."""
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        period_start = now - timedelta(days=period_days)

        # Pre-load all rules for this user to avoid N+1 queries
        rules = self.db.query(Rule).filter(Rule.user_id == user_id).all()
        rules_by_id = {r.id: r for r in rules}

        # Get all unique symbols with alerts
        symbols = (
            self.db.query(Alert.symbol)
            .filter(Alert.user_id == user_id)
            .distinct()
            .all()
        )

        metrics_list = []

        for (symbol,) in symbols:
            metrics = AssetMetrics(symbol=symbol)

            # Get all alerts for this symbol
            alerts = (
                self.db.query(Alert)
                .filter(Alert.user_id == user_id, Alert.symbol == symbol)
                .all()
            )

            metrics.total_alerts = len(alerts)

            # Count alerts in time windows
            metrics.alerts_last_7d = len([
                a for a in alerts if a.triggered_at >= week_ago
            ])
            metrics.alerts_last_30d = len([
                a for a in alerts if a.triggered_at >= period_start
            ])

            # Feedback breakdown
            metrics.feedback = self._get_feedback_breakdown_for_alerts(alerts)

            # Price movement
            metrics.price_movement = self._calculate_price_movement(alerts)

            # Rule type breakdown (using pre-loaded rules)
            rule_type_counts: Dict[str, int] = defaultdict(int)
            for alert in alerts:
                rule = rules_by_id.get(alert.rule_id)
                if rule:
                    rule_type_counts[rule.rule_type] += 1
            metrics.alerts_by_rule_type = dict(rule_type_counts)

            # Find best performing rule for this asset
            rule_usefulness = self._get_rule_usefulness_for_symbol(user_id, symbol)
            if rule_usefulness:
                best_rule_id, best_usefulness = max(
                    rule_usefulness.items(),
                    key=lambda x: x[1]
                )
                metrics.best_rule_id = best_rule_id
                metrics.best_rule_usefulness = best_usefulness

            metrics_list.append(metrics)

        # Sort by total alerts descending
        metrics_list.sort(key=lambda m: m.total_alerts, reverse=True)
        return metrics_list

    def get_rule_performance_report(
        self,
        user_id: str,
        rule_id: str,
        period_days: int = 30
    ) -> Optional[RuleMetrics]:
        """Get detailed performance report for a specific rule."""
        rule = (
            self.db.query(Rule)
            .filter(Rule.id == rule_id, Rule.user_id == user_id)
            .first()
        )
        if not rule:
            return None

        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        period_start = now - timedelta(days=period_days)

        metrics = RuleMetrics(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            symbol=rule.symbol,
            enabled=rule.enabled,
        )

        alerts = self.db.query(Alert).filter(Alert.rule_id == rule.id).all()

        metrics.total_alerts = len(alerts)
        metrics.alerts_last_7d = len([a for a in alerts if a.triggered_at >= week_ago])
        metrics.alerts_last_30d = len([a for a in alerts if a.triggered_at >= period_start])
        metrics.feedback = self._get_feedback_breakdown_for_alerts(alerts)
        metrics.price_movement = self._calculate_price_movement(alerts)

        if alerts:
            latest = max(alerts, key=lambda a: a.triggered_at)
            metrics.last_fired_at = latest.triggered_at

        return metrics

    def get_asset_performance_report(
        self,
        user_id: str,
        symbol: str,
        period_days: int = 30
    ) -> Optional[AssetMetrics]:
        """Get detailed performance report for a specific asset."""
        alerts = (
            self.db.query(Alert)
            .filter(Alert.user_id == user_id, Alert.symbol == symbol.upper())
            .all()
        )

        if not alerts:
            return None

        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        period_start = now - timedelta(days=period_days)

        metrics = AssetMetrics(symbol=symbol.upper())
        metrics.total_alerts = len(alerts)
        metrics.alerts_last_7d = len([a for a in alerts if a.triggered_at >= week_ago])
        metrics.alerts_last_30d = len([a for a in alerts if a.triggered_at >= period_start])
        metrics.feedback = self._get_feedback_breakdown_for_alerts(alerts)
        metrics.price_movement = self._calculate_price_movement(alerts)

        # Rule type breakdown - batch load rules to avoid N+1
        rule_ids = list(set(a.rule_id for a in alerts))
        rules = self.db.query(Rule).filter(Rule.id.in_(rule_ids)).all()
        rules_by_id = {r.id: r for r in rules}

        rule_type_counts: Dict[str, int] = defaultdict(int)
        for alert in alerts:
            rule = rules_by_id.get(alert.rule_id)
            if rule:
                rule_type_counts[rule.rule_type] += 1
        metrics.alerts_by_rule_type = dict(rule_type_counts)

        return metrics

    # Private helper methods

    def _get_feedback_breakdown(self, user_id: str) -> FeedbackBreakdown:
        """Get feedback breakdown for all user alerts."""
        alerts = self.db.query(Alert).filter(Alert.user_id == user_id).all()
        return self._get_feedback_breakdown_for_alerts(alerts)

    def _get_feedback_breakdown_for_alerts(self, alerts: List[Alert]) -> FeedbackBreakdown:
        """Get feedback breakdown for a list of alerts."""
        breakdown = FeedbackBreakdown(total=len(alerts))

        for alert in alerts:
            if alert.feedback == "useful":
                breakdown.useful += 1
            elif alert.feedback == "noise":
                breakdown.noise += 1
            elif alert.feedback == "actionable":
                breakdown.actionable += 1
            else:
                breakdown.unrated += 1

        return breakdown

    def _is_valid_price(self, price) -> bool:
        """Check if a price value is valid (not None, not NaN, and positive)."""
        if price is None:
            return False
        try:
            return not math.isnan(price) and price > 0
        except TypeError:
            return False

    def _calculate_price_movement(self, alerts: List[Alert]) -> PriceMovement:
        """Calculate price movement statistics for a list of alerts."""
        movement = PriceMovement()

        # Filter alerts with valid price data (excluding None, NaN, and non-positive values)
        alerts_3d = [
            a for a in alerts
            if self._is_valid_price(a.price_at_alert) and self._is_valid_price(a.price_after_3d)
        ]
        alerts_7d = [
            a for a in alerts
            if self._is_valid_price(a.price_at_alert) and self._is_valid_price(a.price_after_7d)
        ]
        alerts_30d = [
            a for a in alerts
            if self._is_valid_price(a.price_at_alert) and self._is_valid_price(a.price_after_30d)
        ]

        # 3-day movement
        if alerts_3d:
            changes_3d = [
                ((a.price_after_3d - a.price_at_alert) / a.price_at_alert) * 100
                for a in alerts_3d
            ]
            movement.avg_3d_change_pct = sum(changes_3d) / len(changes_3d)
            movement.positive_3d_rate = (
                len([c for c in changes_3d if c > 0]) / len(changes_3d)
            ) * 100

        # 7-day movement
        if alerts_7d:
            changes_7d = [
                ((a.price_after_7d - a.price_at_alert) / a.price_at_alert) * 100
                for a in alerts_7d
            ]
            movement.avg_7d_change_pct = sum(changes_7d) / len(changes_7d)
            movement.positive_7d_rate = (
                len([c for c in changes_7d if c > 0]) / len(changes_7d)
            ) * 100

        # 30-day movement
        if alerts_30d:
            changes_30d = [
                ((a.price_after_30d - a.price_at_alert) / a.price_at_alert) * 100
                for a in alerts_30d
            ]
            movement.avg_30d_change_pct = sum(changes_30d) / len(changes_30d)
            movement.positive_30d_rate = (
                len([c for c in changes_30d if c > 0]) / len(changes_30d)
            ) * 100

        return movement

    def _find_best_performing_rule(self, user_id: str) -> Optional[str]:
        """Find the rule with highest usefulness rate."""
        rules = self.db.query(Rule).filter(Rule.user_id == user_id).all()

        best_rule = None
        best_rate = -1.0

        for rule in rules:
            alerts = self.db.query(Alert).filter(Alert.rule_id == rule.id).all()
            feedback = self._get_feedback_breakdown_for_alerts(alerts)

            if feedback.rated_count >= 3:  # Minimum sample size
                rate = feedback.usefulness_rate or 0
                if rate > best_rate:
                    best_rate = rate
                    best_rule = rule.name

        return best_rule

    def _find_noisiest_rule(self, user_id: str) -> Optional[str]:
        """Find the rule with highest noise rate."""
        rules = self.db.query(Rule).filter(Rule.user_id == user_id).all()

        noisiest_rule = None
        highest_noise = -1.0

        for rule in rules:
            alerts = self.db.query(Alert).filter(Alert.rule_id == rule.id).all()
            feedback = self._get_feedback_breakdown_for_alerts(alerts)

            if feedback.rated_count >= 3:  # Minimum sample size
                rate = feedback.noise_rate or 0
                if rate > highest_noise:
                    highest_noise = rate
                    noisiest_rule = rule.name

        return noisiest_rule

    def _get_rule_usefulness_for_symbol(
        self,
        user_id: str,
        symbol: str
    ) -> Dict[str, float]:
        """Get usefulness rate per rule for a specific symbol."""
        alerts = (
            self.db.query(Alert)
            .filter(Alert.user_id == user_id, Alert.symbol == symbol)
            .all()
        )

        # Group by rule
        rule_alerts: Dict[str, List[Alert]] = defaultdict(list)
        for alert in alerts:
            rule_alerts[alert.rule_id].append(alert)

        # Calculate usefulness per rule
        result = {}
        for rule_id, rule_alert_list in rule_alerts.items():
            feedback = self._get_feedback_breakdown_for_alerts(rule_alert_list)
            if feedback.rated_count >= 2:  # Minimum sample
                rate = feedback.usefulness_rate
                if rate is not None:
                    result[rule_id] = rate

        return result
