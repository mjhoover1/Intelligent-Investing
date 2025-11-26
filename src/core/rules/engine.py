"""Rule engine for evaluating rules against holdings."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.db.models import Holding, Rule
from src.data.market.provider import MarketDataProvider
from .models import EvaluationResult, RuleType
from .evaluators import get_evaluator

logger = logging.getLogger(__name__)


class RuleEngine:
    """Engine for evaluating rules against portfolio holdings."""

    def __init__(
        self,
        market_provider: MarketDataProvider,
        cooldown_enabled: bool = True,
    ):
        """Initialize the rule engine.

        Args:
            market_provider: Market data provider for fetching prices
            cooldown_enabled: Whether to respect rule cooldown periods
        """
        self.market_provider = market_provider
        self.cooldown_enabled = cooldown_enabled

    def evaluate_all(
        self,
        db: Session,
        user_id: str,
    ) -> List[EvaluationResult]:
        """Evaluate all enabled rules for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of evaluation results for triggered rules
        """
        # Get holdings and rules
        holdings: List[Holding] = (
            db.query(Holding).filter(Holding.user_id == user_id).all()
        )
        rules: List[Rule] = (
            db.query(Rule)
            .filter(Rule.user_id == user_id, Rule.enabled == True)
            .all()
        )

        if not holdings:
            logger.debug("No holdings found for user")
            return []

        logger.info(f"Evaluating {len(rules)} rule(s) against {len(holdings)} holding(s)")

        # Build symbol -> holdings map
        holdings_by_symbol: Dict[str, List[Holding]] = {}
        for h in holdings:
            holdings_by_symbol.setdefault(h.symbol, []).append(h)

        # Prefetch prices for all symbols
        all_symbols = list(holdings_by_symbol.keys())
        prices = self.market_provider.get_prices(all_symbols, db)

        results: List[EvaluationResult] = []

        skipped_cooldown = 0
        for rule in rules:
            # Check cooldown
            if self._is_in_cooldown(rule):
                skipped_cooldown += 1
                continue

            # Determine which symbols this rule applies to
            target_symbols = (
                [rule.symbol] if rule.symbol else list(holdings_by_symbol.keys())
            )

            # Get evaluator for this rule type
            evaluator = get_evaluator(RuleType(rule.rule_type))
            if evaluator is None:
                continue

            for symbol in target_symbols:
                symbol_holdings = holdings_by_symbol.get(symbol, [])
                if not symbol_holdings:
                    continue

                current_price = prices.get(symbol)
                if current_price is None:
                    continue

                # Use first holding's cost basis (could average if multiple)
                holding = symbol_holdings[0]

                # Evaluate the condition
                triggered = evaluator.evaluate(
                    current_price=current_price,
                    cost_basis=holding.cost_basis,
                    threshold=rule.threshold,
                )

                if triggered:
                    reason = evaluator.format_reason(
                        current_price=current_price,
                        cost_basis=holding.cost_basis,
                        threshold=rule.threshold,
                    )

                    results.append(
                        EvaluationResult(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            rule_type=RuleType(rule.rule_type),
                            symbol=symbol,
                            triggered=True,
                            reason=reason,
                            current_price=current_price,
                            cost_basis=holding.cost_basis,
                            threshold=rule.threshold,
                            holding_id=holding.id,
                        )
                    )

        if skipped_cooldown > 0:
            logger.debug(f"Skipped {skipped_cooldown} rule(s) due to cooldown")

        logger.info(f"Evaluation complete: {len(results)} rule(s) triggered")
        return results

    def evaluate_rule(
        self,
        db: Session,
        rule: Rule,
        holdings: List[Holding],
        ignore_cooldown: bool = False,
    ) -> List[EvaluationResult]:
        """Evaluate a single rule against holdings.

        Args:
            db: Database session
            rule: Rule to evaluate
            holdings: Holdings to evaluate against
            ignore_cooldown: Whether to ignore cooldown

        Returns:
            List of evaluation results
        """
        if not ignore_cooldown and self._is_in_cooldown(rule):
            return []

        # Build symbol -> holdings map
        holdings_by_symbol: Dict[str, List[Holding]] = {}
        for h in holdings:
            holdings_by_symbol.setdefault(h.symbol, []).append(h)

        # Determine target symbols
        target_symbols = (
            [rule.symbol] if rule.symbol else list(holdings_by_symbol.keys())
        )

        # Fetch prices
        prices = self.market_provider.get_prices(target_symbols, db)

        evaluator = get_evaluator(RuleType(rule.rule_type))
        if evaluator is None:
            return []

        results: List[EvaluationResult] = []

        for symbol in target_symbols:
            symbol_holdings = holdings_by_symbol.get(symbol, [])
            if not symbol_holdings:
                continue

            current_price = prices.get(symbol)
            if current_price is None:
                continue

            holding = symbol_holdings[0]

            triggered = evaluator.evaluate(
                current_price=current_price,
                cost_basis=holding.cost_basis,
                threshold=rule.threshold,
            )

            if triggered:
                reason = evaluator.format_reason(
                    current_price=current_price,
                    cost_basis=holding.cost_basis,
                    threshold=rule.threshold,
                )

                results.append(
                    EvaluationResult(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        rule_type=RuleType(rule.rule_type),
                        symbol=symbol,
                        triggered=True,
                        reason=reason,
                        current_price=current_price,
                        cost_basis=holding.cost_basis,
                        threshold=rule.threshold,
                        holding_id=holding.id,
                    )
                )

        return results

    def _is_in_cooldown(self, rule: Rule) -> bool:
        """Check if a rule is in cooldown period.

        Args:
            rule: Rule to check

        Returns:
            True if rule is in cooldown
        """
        if not self.cooldown_enabled:
            return False

        if not rule.last_triggered_at:
            return False

        if not rule.cooldown_minutes:
            return False

        cooldown_end = rule.last_triggered_at + timedelta(minutes=rule.cooldown_minutes)
        return datetime.utcnow() < cooldown_end
