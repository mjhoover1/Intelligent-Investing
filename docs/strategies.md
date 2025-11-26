# Strategy Presets Guide

Strategy presets are pre-configured rule bundles designed for common investment styles. Apply them with one click to get started quickly.

> **Disclaimer**: These strategies are informational frameworks only. They do not constitute investment advice. Past performance does not guarantee future results.

---

## Overview

| Strategy | Risk Level | Alert Frequency | Best For |
|----------|------------|-----------------|----------|
| Capital Preservation | Conservative | Low | Loss protection |
| Swing Trader | Medium | Medium | Momentum trading |
| Dip Hunter | Aggressive | Medium-High | Finding entries |
| Momentum Rider | Aggressive | Medium | Riding uptrends |
| Recovery Tracker | Conservative | Low | Underwater positions |
| Long Term Holder | Conservative | Very Low | Buy and hold |
| Active Trader | Medium | High | Active management |

---

## Capital Preservation

**ID**: `capital-preservation`
**Risk Level**: Conservative
**Category**: Protection

### Description

Protect your portfolio from significant losses with early warning alerts at key drawdown levels. Designed for investors who prioritize capital protection over maximum returns.

### Rules Applied

| Rule Name | Type | Threshold | Cooldown | Purpose |
|-----------|------|-----------|----------|---------|
| Early Warning (-15%) | `price_below_cost_pct` | 15% | 24 hours | First alert - review your thesis |
| Stop Loss Warning (-25%) | `price_below_cost_pct` | 25% | 12 hours | Serious drawdown - consider action |
| Critical Loss (-40%) | `price_below_cost_pct` | 40% | 4 hours | Major loss - urgent review |

### Who Should Use This

- Retirees or those protecting accumulated wealth
- Risk-averse investors
- Anyone who wants early warning before losses compound
- Investors who sleep better knowing they have guardrails

### What to Expect

- **Alert frequency**: Low to moderate (depends on market conditions)
- **False positives**: Some during normal volatility
- **Typical action**: Review position when alerted, decide if thesis still holds

### CLI

```bash
invest strategies apply capital-preservation
```

---

## Swing Trader

**ID**: `swing-trader`
**Risk Level**: Medium
**Category**: Profit

### Description

Capture profits on momentum swings using a combination of price and RSI signals. Balanced approach for traders who want to lock in gains and find oversold entries.

### Rules Applied

| Rule Name | Type | Threshold | Cooldown | Purpose |
|-----------|------|-----------|----------|---------|
| Take Profit (+25%) | `price_above_cost_pct` | 25% | 24 hours | Consider partial profits |
| Strong Profit (+50%) | `price_above_cost_pct` | 50% | 24 hours | Excellent gain - lock some in |
| RSI Overbought | `rsi_above_value` | 70 | 24 hours | Momentum may be exhausted |
| RSI Oversold Entry | `rsi_below_value` | 30 | 24 hours | Potential buying opportunity |

### Who Should Use This

- Part-time traders who check positions regularly
- Investors who want to actively manage positions
- Those comfortable with technical indicators
- Anyone who wants a balanced alert mix

### What to Expect

- **Alert frequency**: Moderate
- **Typical actions**: Trim winners at profit targets, add on oversold signals
- **Best combined with**: Some loss protection rules

### CLI

```bash
invest strategies apply swing-trader
```

---

## Dip Hunter

**ID**: `dip-hunter`
**Risk Level**: Aggressive
**Category**: Opportunity

### Description

Find oversold opportunities for adding to positions. Designed for investors who view pullbacks as buying opportunities rather than reasons to sell.

### Rules Applied

| Rule Name | Type | Threshold | Cooldown | Purpose |
|-----------|------|-----------|----------|---------|
| Minor Dip (-10%) | `price_below_cost_pct` | 10% | 48 hours | Small pullback - start watching |
| Significant Dip (-20%) | `price_below_cost_pct` | 20% | 24 hours | Good dip - consider averaging down |
| Deep Oversold (RSI < 25) | `rsi_below_value` | 25 | 12 hours | Deeply oversold - high conviction zone |

### Who Should Use This

- Contrarian investors
- Those with cash reserves ready to deploy
- Investors who believe in their positions long-term
- Risk-tolerant individuals comfortable buying into weakness

### What to Expect

- **Alert frequency**: Medium to high during corrections
- **Typical actions**: Research and potentially add to positions
- **Warning**: Catching falling knives can be painful - use with risk management

### CLI

```bash
invest strategies apply dip-hunter
```

---

## Momentum Rider

**ID**: `momentum-rider`
**Risk Level**: Aggressive
**Category**: Profit

### Description

Ride strong uptrends and exit before reversals. Aggressive strategy focused on maximizing gains during bull runs while watching for exhaustion signals.

### Rules Applied

| Rule Name | Type | Threshold | Cooldown | Purpose |
|-----------|------|-----------|----------|---------|
| Momentum Start (+15%) | `price_above_cost_pct` | 15% | 24 hours | Position gaining traction |
| Momentum Strong (+35%) | `price_above_cost_pct` | 35% | 24 hours | Strong run - trail your stop |
| Moonshot (+100%) | `price_above_cost_pct` | 100% | 12 hours | Doubled! Consider taking cost off |
| Overbought Warning | `rsi_above_value` | 75 | 12 hours | Extreme RSI - prepare for pullback |

### Who Should Use This

- Growth investors
- Those holding high-beta stocks
- Investors comfortable with volatility
- Anyone who wants help knowing when to take profits

### What to Expect

- **Alert frequency**: High during bull markets, low during corrections
- **Typical actions**: Trail stops higher, take partial profits at targets
- **Best combined with**: Loss protection rules for risk management

### CLI

```bash
invest strategies apply momentum-rider
```

---

## Recovery Tracker

**ID**: `recovery-tracker`
**Risk Level**: Conservative
**Category**: Balanced

### Description

Track underwater positions recovering toward breakeven. Helpful for monitoring losers you're holding, so you can make informed decisions as they recover (or don't).

### Rules Applied

| Rule Name | Type | Threshold | Cooldown | Purpose |
|-----------|------|-----------|----------|---------|
| Recovery Started | `price_above_cost_pct` | -10% | 48 hours | Still down 10% but improving |
| Near Breakeven | `price_above_cost_pct` | -2% | 24 hours | Almost even - decision time |
| Breakeven Reached | `price_above_cost_pct` | 0% | 24 hours | Back to even! Hold or exit? |

### Who Should Use This

- Investors holding underwater positions
- Those debating whether to hold or sell losers
- Anyone who wants to track recovery progress
- Tax-loss harvesting decision makers

### What to Expect

- **Alert frequency**: Low (only during recovery)
- **Typical actions**: Decide to hold through recovery or exit at breakeven
- **Mental benefit**: Clear milestones help with emotional decisions

### CLI

```bash
invest strategies apply recovery-tracker
```

---

## Long Term Holder

**ID**: `long-term-holder`
**Risk Level**: Conservative
**Category**: Balanced

### Description

Minimal alerts for buy-and-hold investors. Only major events trigger notifications, keeping noise low while ensuring you don't miss significant moves.

### Rules Applied

| Rule Name | Type | Threshold | Cooldown | Purpose |
|-----------|------|-----------|----------|---------|
| Major Drawdown (-30%) | `price_below_cost_pct` | 30% | 1 week | Significant drop - but don't panic |
| Crash Alert (-50%) | `price_below_cost_pct` | 50% | 3 days | Major loss - is thesis broken? |
| Big Winner (+100%) | `price_above_cost_pct` | 100% | 1 week | Doubled - consider rebalancing |

### Who Should Use This

- True buy-and-hold investors
- Those who don't want constant alerts
- Investors focused on the long game
- Anyone who gets anxious from frequent notifications

### What to Expect

- **Alert frequency**: Very low (major moves only)
- **Typical actions**: Review thesis, consider rebalancing
- **Philosophy**: Set and forget, only surface truly important events

### CLI

```bash
invest strategies apply long-term-holder
```

---

## Active Trader

**ID**: `active-trader`
**Risk Level**: Medium
**Category**: Balanced

### Description

Comprehensive alerts for hands-on portfolio management. The most complete preset covering losses, gains, and RSI signals across multiple thresholds.

### Rules Applied

| Rule Name | Type | Threshold | Cooldown | Purpose |
|-----------|------|-----------|----------|---------|
| Small Loss (-10%) | `price_below_cost_pct` | 10% | 24 hours | Minor pullback |
| Medium Loss (-20%) | `price_below_cost_pct` | 20% | 12 hours | Notable drawdown |
| Large Loss (-35%) | `price_below_cost_pct` | 35% | 4 hours | Significant loss |
| Small Gain (+15%) | `price_above_cost_pct` | 15% | 24 hours | Nice gain |
| Good Gain (+30%) | `price_above_cost_pct` | 30% | 24 hours | Solid profit |
| Great Gain (+50%) | `price_above_cost_pct` | 50% | 24 hours | Excellent profit |
| RSI Oversold | `rsi_below_value` | 30 | 24 hours | Oversold condition |
| RSI Overbought | `rsi_above_value` | 70 | 24 hours | Overbought condition |

### Who Should Use This

- Active traders who want full visibility
- Those managing a diverse portfolio
- Investors who check positions daily
- Anyone who wants all the data points

### What to Expect

- **Alert frequency**: High (8 rules × number of positions)
- **Typical actions**: Daily review and position management
- **Consider**: Starting here and disabling rules you find too noisy

### CLI

```bash
invest strategies apply active-trader
```

---

## Combining Strategies

You can apply multiple strategies. Rules from different strategies stack:

```bash
# Protection + Profit taking
invest strategies apply capital-preservation
invest strategies apply swing-trader
```

To remove a strategy's rules:

```bash
# View rules from a specific strategy
invest rules list | grep "\[swing-trader\]"

# Delete specific rules by ID
invest rules delete RULE_ID
```

---

## Creating Custom Strategies

If presets don't fit your style, create custom rules:

```bash
# Mix and match
invest rules add "My Entry Alert" rsi_below_value 28
invest rules add "My Exit Alert" price_above_cost_pct 40
invest rules add "My Stop Loss" price_below_cost_pct 18 --symbol TSLA
```

---

## Strategy Comparison

| Need | Best Strategy |
|------|---------------|
| Protect against losses | Capital Preservation |
| Find buying dips | Dip Hunter |
| Take profits on winners | Swing Trader or Momentum Rider |
| Minimal notifications | Long Term Holder |
| Track underwater positions | Recovery Tracker |
| See everything | Active Trader |

---

*See [Rule Types](./rule-types.md) for detailed rule documentation.*
