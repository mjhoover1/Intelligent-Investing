"""Prompt templates for AI context generation."""

from typing import Optional

# Base prompt for alert context with enriched technical data
ALERT_CONTEXT_PROMPT = """You are a neutral financial explainer. This is NOT financial advice.

Given the following alert data, explain what happened and what factors might be relevant, in under 150 words.

Data:
- Symbol: {symbol}
- Alert: {rule_name}
- Rule Type: {rule_type}
- Threshold: {threshold}
- Current Price: ${current_price:.2f}
{cost_basis_line}
{percent_change_line}
{technical_lines}
- Alert Message: {message}

Provide factual context only. Mention:
1. What triggered the alert
2. The significance of the price movement or indicator signal
3. Technical context (RSI zones: oversold < 30, overbought > 70; 52-week positioning)
4. Any general factors that might be relevant

Do NOT tell the user what to do. End with: "This is not financial advice."
"""


def build_alert_prompt(
    symbol: str,
    rule_name: str,
    rule_type: str,
    threshold: float,
    current_price: float,
    message: str,
    cost_basis: Optional[float] = None,
    percent_change: Optional[float] = None,
    rsi: Optional[float] = None,
    indicator_value: Optional[float] = None,
    high_52_week: Optional[float] = None,
    low_52_week: Optional[float] = None,
) -> str:
    """Build the alert context prompt.

    Args:
        symbol: Stock symbol
        rule_name: Name of the rule that triggered
        rule_type: Type of rule
        threshold: Rule threshold
        current_price: Current price
        message: Alert message
        cost_basis: Optional cost basis
        percent_change: Optional percent change from cost basis
        rsi: Optional RSI value
        indicator_value: Optional indicator value (for indicator rules)
        high_52_week: Optional 52-week high
        low_52_week: Optional 52-week low

    Returns:
        Formatted prompt string
    """
    # Build optional lines
    cost_basis_line = ""
    if cost_basis is not None:
        cost_basis_line = f"- Cost Basis: ${cost_basis:.2f}"

    percent_change_line = ""
    if percent_change is not None:
        direction = "up" if percent_change > 0 else "down"
        percent_change_line = f"- Change from Cost: {percent_change:+.1f}% ({direction})"

    # Build technical indicator lines
    technical_parts = []

    # RSI info
    if rsi is not None:
        zone = "oversold" if rsi < 30 else ("overbought" if rsi > 70 else "neutral")
        technical_parts.append(f"- RSI (14-day): {rsi:.1f} ({zone})")
    elif indicator_value is not None and "rsi" in rule_type.lower():
        zone = (
            "oversold" if indicator_value < 30 else ("overbought" if indicator_value > 70 else "neutral")
        )
        technical_parts.append(f"- RSI (14-day): {indicator_value:.1f} ({zone})")

    # 52-week range
    if high_52_week is not None and low_52_week is not None:
        pct_from_high = ((current_price - high_52_week) / high_52_week) * 100
        pct_from_low = ((current_price - low_52_week) / low_52_week) * 100
        technical_parts.append(
            f"- 52-Week Range: ${low_52_week:.2f} - ${high_52_week:.2f}"
        )
        technical_parts.append(
            f"- Position in 52wk Range: {pct_from_high:+.1f}% from high, {pct_from_low:+.1f}% from low"
        )

    technical_lines = "\n".join(technical_parts) if technical_parts else ""

    return ALERT_CONTEXT_PROMPT.format(
        symbol=symbol,
        rule_name=rule_name,
        rule_type=rule_type,
        threshold=threshold,
        current_price=current_price,
        cost_basis_line=cost_basis_line,
        percent_change_line=percent_change_line,
        technical_lines=technical_lines,
        message=message,
    )
