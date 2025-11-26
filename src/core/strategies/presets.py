"""Strategy presets - one-click rule bundles for common investment strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from src.core.rules.models import RuleType


@dataclass
class RuleTemplate:
    """Template for creating a rule as part of a strategy."""

    name: str
    rule_type: RuleType
    threshold: float
    symbol: Optional[str] = None  # None = applies to all holdings
    cooldown_minutes: int = 1440  # Default 24 hours
    description: str = ""


@dataclass
class StrategyPreset:
    """A named collection of rule templates that work together."""

    id: str
    name: str
    description: str
    category: str  # 'protection', 'profit', 'opportunity', 'balanced'
    rules: List[RuleTemplate] = field(default_factory=list)
    risk_level: str = "medium"  # 'conservative', 'medium', 'aggressive'

    def __post_init__(self):
        # Prefix rule names with strategy name for clarity
        for rule in self.rules:
            if not rule.name.startswith(f"[{self.id}]"):
                rule.name = f"[{self.id}] {rule.name}"


# =============================================================================
# STRATEGY PRESETS
# =============================================================================

CAPITAL_PRESERVATION = StrategyPreset(
    id="capital-preservation",
    name="Capital Preservation",
    description="Protect your portfolio from significant losses with early warning alerts.",
    category="protection",
    risk_level="conservative",
    rules=[
        RuleTemplate(
            name="Early Warning (-15%)",
            rule_type=RuleType.PRICE_BELOW_COST_PCT,
            threshold=15.0,
            cooldown_minutes=1440,
            description="Alert when a position drops 15% - time to review thesis",
        ),
        RuleTemplate(
            name="Stop Loss Warning (-25%)",
            rule_type=RuleType.PRICE_BELOW_COST_PCT,
            threshold=25.0,
            cooldown_minutes=720,
            description="Serious drawdown - consider reducing position",
        ),
        RuleTemplate(
            name="Critical Loss (-40%)",
            rule_type=RuleType.PRICE_BELOW_COST_PCT,
            threshold=40.0,
            cooldown_minutes=240,
            description="Major loss - urgent review required",
        ),
    ],
)

SWING_TRADER = StrategyPreset(
    id="swing-trader",
    name="Swing Trader",
    description="Capture profits on momentum swings using price and RSI signals.",
    category="profit",
    risk_level="medium",
    rules=[
        RuleTemplate(
            name="Take Profit (+25%)",
            rule_type=RuleType.PRICE_ABOVE_COST_PCT,
            threshold=25.0,
            cooldown_minutes=1440,
            description="Consider taking partial profits",
        ),
        RuleTemplate(
            name="Strong Profit (+50%)",
            rule_type=RuleType.PRICE_ABOVE_COST_PCT,
            threshold=50.0,
            cooldown_minutes=1440,
            description="Excellent gain - lock in some profits",
        ),
        RuleTemplate(
            name="RSI Overbought",
            rule_type=RuleType.RSI_ABOVE_VALUE,
            threshold=70.0,
            cooldown_minutes=1440,
            description="Stock may be overextended - watch for reversal",
        ),
        RuleTemplate(
            name="RSI Oversold Entry",
            rule_type=RuleType.RSI_BELOW_VALUE,
            threshold=30.0,
            cooldown_minutes=1440,
            description="Potential buying opportunity",
        ),
    ],
)

DIP_HUNTER = StrategyPreset(
    id="dip-hunter",
    name="Dip Hunter",
    description="Find oversold opportunities for adding to positions.",
    category="opportunity",
    risk_level="aggressive",
    rules=[
        RuleTemplate(
            name="Minor Dip (-10%)",
            rule_type=RuleType.PRICE_BELOW_COST_PCT,
            threshold=10.0,
            cooldown_minutes=2880,  # 48 hours
            description="Small pullback - watch for entry",
        ),
        RuleTemplate(
            name="Significant Dip (-20%)",
            rule_type=RuleType.PRICE_BELOW_COST_PCT,
            threshold=20.0,
            cooldown_minutes=1440,
            description="Good dip - consider averaging down",
        ),
        RuleTemplate(
            name="Deep Oversold (RSI < 25)",
            rule_type=RuleType.RSI_BELOW_VALUE,
            threshold=25.0,
            cooldown_minutes=720,
            description="Deeply oversold - high conviction entry zone",
        ),
    ],
)

MOMENTUM_RIDER = StrategyPreset(
    id="momentum-rider",
    name="Momentum Rider",
    description="Ride strong uptrends and exit before reversals.",
    category="profit",
    risk_level="aggressive",
    rules=[
        RuleTemplate(
            name="Momentum Start (+15%)",
            rule_type=RuleType.PRICE_ABOVE_COST_PCT,
            threshold=15.0,
            cooldown_minutes=1440,
            description="Position gaining momentum",
        ),
        RuleTemplate(
            name="Momentum Strong (+35%)",
            rule_type=RuleType.PRICE_ABOVE_COST_PCT,
            threshold=35.0,
            cooldown_minutes=1440,
            description="Strong run - trail your stop",
        ),
        RuleTemplate(
            name="Moonshot (+100%)",
            rule_type=RuleType.PRICE_ABOVE_COST_PCT,
            threshold=100.0,
            cooldown_minutes=720,
            description="Double! Consider taking original investment off table",
        ),
        RuleTemplate(
            name="Overbought Warning",
            rule_type=RuleType.RSI_ABOVE_VALUE,
            threshold=75.0,
            cooldown_minutes=720,
            description="Extreme RSI - prepare for pullback",
        ),
    ],
)

RECOVERY_TRACKER = StrategyPreset(
    id="recovery-tracker",
    name="Recovery Tracker",
    description="Track underwater positions recovering toward breakeven.",
    category="balanced",
    risk_level="conservative",
    rules=[
        RuleTemplate(
            name="Recovery Started",
            rule_type=RuleType.PRICE_ABOVE_COST_PCT,
            threshold=-10.0,  # Still down 10% but recovering
            cooldown_minutes=2880,
            description="Position recovering - down only 10%",
        ),
        RuleTemplate(
            name="Near Breakeven",
            rule_type=RuleType.PRICE_ABOVE_COST_PCT,
            threshold=-2.0,
            cooldown_minutes=1440,
            description="Almost breakeven - decision time",
        ),
        RuleTemplate(
            name="Breakeven Reached",
            rule_type=RuleType.PRICE_ABOVE_COST_PCT,
            threshold=0.0,
            cooldown_minutes=1440,
            description="Back to even! Continue holding or exit?",
        ),
    ],
)

LONG_TERM_HOLDER = StrategyPreset(
    id="long-term-holder",
    name="Long Term Holder",
    description="Minimal alerts for buy-and-hold investors. Only major events.",
    category="balanced",
    risk_level="conservative",
    rules=[
        RuleTemplate(
            name="Major Drawdown (-30%)",
            rule_type=RuleType.PRICE_BELOW_COST_PCT,
            threshold=30.0,
            cooldown_minutes=10080,  # 1 week
            description="Significant drop - review but don't panic",
        ),
        RuleTemplate(
            name="Crash Alert (-50%)",
            rule_type=RuleType.PRICE_BELOW_COST_PCT,
            threshold=50.0,
            cooldown_minutes=4320,  # 3 days
            description="Major loss - thesis broken?",
        ),
        RuleTemplate(
            name="Big Winner (+100%)",
            rule_type=RuleType.PRICE_ABOVE_COST_PCT,
            threshold=100.0,
            cooldown_minutes=10080,
            description="Doubled! Consider rebalancing",
        ),
    ],
)

ACTIVE_TRADER = StrategyPreset(
    id="active-trader",
    name="Active Trader",
    description="Comprehensive alerts for hands-on portfolio management.",
    category="balanced",
    risk_level="medium",
    rules=[
        RuleTemplate(
            name="Small Loss (-10%)",
            rule_type=RuleType.PRICE_BELOW_COST_PCT,
            threshold=10.0,
            cooldown_minutes=1440,
            description="Minor pullback",
        ),
        RuleTemplate(
            name="Medium Loss (-20%)",
            rule_type=RuleType.PRICE_BELOW_COST_PCT,
            threshold=20.0,
            cooldown_minutes=720,
            description="Notable drawdown",
        ),
        RuleTemplate(
            name="Large Loss (-35%)",
            rule_type=RuleType.PRICE_BELOW_COST_PCT,
            threshold=35.0,
            cooldown_minutes=240,
            description="Significant loss - review needed",
        ),
        RuleTemplate(
            name="Small Gain (+15%)",
            rule_type=RuleType.PRICE_ABOVE_COST_PCT,
            threshold=15.0,
            cooldown_minutes=1440,
            description="Nice gain",
        ),
        RuleTemplate(
            name="Good Gain (+30%)",
            rule_type=RuleType.PRICE_ABOVE_COST_PCT,
            threshold=30.0,
            cooldown_minutes=1440,
            description="Solid profit",
        ),
        RuleTemplate(
            name="Great Gain (+50%)",
            rule_type=RuleType.PRICE_ABOVE_COST_PCT,
            threshold=50.0,
            cooldown_minutes=1440,
            description="Excellent - consider profit taking",
        ),
        RuleTemplate(
            name="RSI Oversold",
            rule_type=RuleType.RSI_BELOW_VALUE,
            threshold=30.0,
            cooldown_minutes=1440,
            description="Oversold condition",
        ),
        RuleTemplate(
            name="RSI Overbought",
            rule_type=RuleType.RSI_ABOVE_VALUE,
            threshold=70.0,
            cooldown_minutes=1440,
            description="Overbought condition",
        ),
    ],
)


# =============================================================================
# PRESET REGISTRY
# =============================================================================

PRESETS: dict[str, StrategyPreset] = {
    "capital-preservation": CAPITAL_PRESERVATION,
    "swing-trader": SWING_TRADER,
    "dip-hunter": DIP_HUNTER,
    "momentum-rider": MOMENTUM_RIDER,
    "recovery-tracker": RECOVERY_TRACKER,
    "long-term-holder": LONG_TERM_HOLDER,
    "active-trader": ACTIVE_TRADER,
}


def get_preset(preset_id: str) -> Optional[StrategyPreset]:
    """Get a strategy preset by ID.

    Args:
        preset_id: Preset identifier

    Returns:
        StrategyPreset or None if not found
    """
    return PRESETS.get(preset_id.lower())


def list_presets() -> List[StrategyPreset]:
    """Get all available strategy presets.

    Returns:
        List of all presets
    """
    return list(PRESETS.values())
