# Rule Types Reference

Signal Sentinel supports six rule types for monitoring your portfolio. This guide explains each type, when to use it, and provides example configurations.

> **Reminder**: All alerts are informational. They do not constitute financial advice.

---

## Overview

| Rule Type | Description | Threshold Unit |
|-----------|-------------|----------------|
| `price_below_cost_pct` | Price dropped X% below cost basis | Percentage |
| `price_above_cost_pct` | Price rose X% above cost basis | Percentage |
| `price_below_value` | Price dropped below $X | Dollars |
| `price_above_value` | Price rose above $X | Dollars |
| `rsi_below_value` | RSI dropped below X | RSI value (0-100) |
| `rsi_above_value` | RSI rose above X | RSI value (0-100) |

---

## Price-Based Rules

### `price_below_cost_pct`

**What it does**: Alerts when a position's current price is X% below your cost basis.

**Threshold**: Percentage (e.g., `15` means 15% below cost)

**Use cases**:
- Stop-loss warnings
- Drawdown monitoring
- Tax-loss harvesting opportunities

**Examples**:

```bash
# Alert when any stock drops 20% below cost
invest rules add "Drawdown Warning" price_below_cost_pct 20

# Alert for a specific stock at 15%
invest rules add "TSLA Stop Loss" price_below_cost_pct 15 --symbol TSLA

# Aggressive dip-buying alert at 30%
invest rules add "Deep Value Alert" price_below_cost_pct 30
```

**Typical thresholds**:
- 10-15%: Minor pullback / early warning
- 20-25%: Significant drawdown / stop-loss territory
- 30-40%: Major loss / thesis review needed
- 50%+: Crisis alert / consider exiting

---

### `price_above_cost_pct`

**What it does**: Alerts when a position's current price is X% above your cost basis.

**Threshold**: Percentage (e.g., `25` means 25% profit)

**Use cases**:
- Profit-taking reminders
- Position rebalancing triggers
- Tracking recovery of underwater positions

**Examples**:

```bash
# Alert at 25% profit
invest rules add "Take Profit" price_above_cost_pct 25

# Alert when doubled
invest rules add "100% Winner" price_above_cost_pct 100

# Track recovery (still down 10% but improving)
invest rules add "Recovery Check" price_above_cost_pct -10
```

**Typical thresholds**:
- 15-25%: Initial profit-taking zone
- 30-50%: Solid gains / consider trimming
- 75-100%: Exceptional gains / rebalance
- 100%+: Consider taking original investment off table

**Note**: Negative thresholds work too! `-10` means "alert when only down 10%" (useful for tracking recovery).

---

### `price_below_value`

**What it does**: Alerts when a stock's price drops below a specific dollar amount.

**Threshold**: Dollar value (e.g., `50` means alert below $50)

**Use cases**:
- Absolute price targets
- Support level monitoring
- Entry point watching

**Examples**:

```bash
# Alert if AAPL drops below $150
invest rules add "AAPL Support" price_below_value 150 --symbol AAPL

# Alert if NVDA drops below $400
invest rules add "NVDA Entry Zone" price_below_value 400 --symbol NVDA
```

**Best practices**:
- Always specify a symbol (rule makes no sense across different stocks)
- Base thresholds on technical support levels
- Consider cost basis for context

---

### `price_above_value`

**What it does**: Alerts when a stock's price rises above a specific dollar amount.

**Threshold**: Dollar value (e.g., `200` means alert above $200)

**Use cases**:
- Resistance level monitoring
- Target price alerts
- Breakout detection

**Examples**:

```bash
# Alert if AAPL breaks $200
invest rules add "AAPL Breakout" price_above_value 200 --symbol AAPL

# Alert if MSFT hits $500
invest rules add "MSFT Target" price_above_value 500 --symbol MSFT
```

---

## RSI-Based Rules

RSI (Relative Strength Index) measures momentum on a 0-100 scale. Signal Sentinel uses 14-day RSI by default.

### `rsi_below_value`

**What it does**: Alerts when a stock's RSI drops below a threshold (oversold signal).

**Threshold**: RSI value from 0-100 (e.g., `30` means RSI < 30)

**Use cases**:
- Finding oversold buying opportunities
- Identifying capitulation
- Dip-hunting

**RSI zones**:
- 0-30: **Oversold** - potential buying opportunity
- 30-50: Bearish momentum
- 50: Neutral
- 50-70: Bullish momentum
- 70-100: **Overbought** - potential selling opportunity

**Examples**:

```bash
# Classic oversold signal
invest rules add "RSI Oversold" rsi_below_value 30

# Extremely oversold (high conviction)
invest rules add "Deep Oversold" rsi_below_value 25

# Watch for weakness starting
invest rules add "RSI Weakness" rsi_below_value 40
```

**Typical thresholds**:
- 25-30: Classic oversold (most common)
- 20-25: Deeply oversold (higher conviction)
- 35-40: Early warning of weakness

---

### `rsi_above_value`

**What it does**: Alerts when a stock's RSI rises above a threshold (overbought signal).

**Threshold**: RSI value from 0-100 (e.g., `70` means RSI > 70)

**Use cases**:
- Identifying overbought conditions
- Profit-taking timing
- Reversal warnings

**Examples**:

```bash
# Classic overbought signal
invest rules add "RSI Overbought" rsi_above_value 70

# Extremely overbought
invest rules add "RSI Extreme" rsi_above_value 80

# Early overbought warning
invest rules add "RSI Hot" rsi_above_value 65
```

**Typical thresholds**:
- 65-70: Starting to get overbought
- 70-75: Classic overbought (most common)
- 75-80: Very overbought
- 80+: Extremely overbought (reversal likely)

---

## Common Rule Parameters

All rules support these parameters:

### Symbol (Optional)

```bash
# Apply to all holdings (no --symbol)
invest rules add "Global Rule" price_below_cost_pct 20

# Apply to specific stock
invest rules add "AAPL Rule" price_below_cost_pct 20 --symbol AAPL
```

### Cooldown Period

Prevents alert spam by waiting before re-triggering:

```bash
# Default: 60 minutes
invest rules add "Rule" price_below_cost_pct 20

# Custom: 24 hours (1440 minutes)
invest rules add "Rule" price_below_cost_pct 20 --cooldown 1440

# Short: 4 hours
invest rules add "Rule" price_below_cost_pct 20 --cooldown 240
```

**Recommended cooldowns**:
- Minor alerts: 1440 minutes (24 hours)
- Important alerts: 720 minutes (12 hours)
- Critical alerts: 240 minutes (4 hours)
- Very critical: 60 minutes (1 hour)

### Enable/Disable

```bash
# Disable a rule temporarily
invest rules update RULE_ID --disable

# Re-enable
invest rules update RULE_ID --enable
```

---

## Rule Combinations

### Capital Preservation Stack

```bash
invest rules add "Warning" price_below_cost_pct 15 --cooldown 1440
invest rules add "Alert" price_below_cost_pct 25 --cooldown 720
invest rules add "Critical" price_below_cost_pct 40 --cooldown 240
```

### Swing Trading Stack

```bash
invest rules add "Entry Signal" rsi_below_value 30 --cooldown 1440
invest rules add "Exit Signal" rsi_above_value 70 --cooldown 1440
invest rules add "Take Profit" price_above_cost_pct 25 --cooldown 1440
```

### Momentum Stack

```bash
invest rules add "Momentum Start" price_above_cost_pct 15 --cooldown 1440
invest rules add "Strong Momentum" price_above_cost_pct 35 --cooldown 1440
invest rules add "Moonshot" price_above_cost_pct 100 --cooldown 720
invest rules add "Overbought Warning" rsi_above_value 75 --cooldown 720
```

---

## Pro Tips

1. **Layer your rules**: Use multiple thresholds for the same condition (e.g., 15%, 25%, 40% drawdown alerts).

2. **Use RSI with price rules**: RSI tells you momentum; price tells you your P&L. Combine them.

3. **Adjust cooldowns for volatility**: Shorter cooldowns for volatile stocks, longer for stable ones.

4. **Start conservative**: Begin with wider thresholds and tighten based on your tolerance.

5. **Rate your alerts**: Use the feedback system to learn which rules work for you.

---

*See [Strategy Presets](./strategies.md) for pre-built rule combinations.*
