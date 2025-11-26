"""Prompt templates for AI context generation."""

# Base prompt for alert context
ALERT_CONTEXT_PROMPT = """You are a neutral financial explainer. This is NOT financial advice.

Given the following alert data, explain what happened and what factors might be relevant, in under 120 words.

Data:
- Symbol: {symbol}
- Alert: {rule_name}
- Rule Type: {rule_type}
- Threshold: {threshold}
- Current Price: ${current_price:.2f}
{cost_basis_line}
{percent_change_line}
- Alert Message: {message}

Provide factual context only. Mention:
1. What triggered the alert
2. The significance of the price movement
3. Any general factors that might be relevant (market conditions, sector trends)

Do NOT tell the user what to do. End with: "This is not financial advice."
"""


def build_alert_prompt(
    symbol: str,
    rule_name: str,
    rule_type: str,
    threshold: float,
    current_price: float,
    message: str,
    cost_basis: float = None,
    percent_change: float = None,
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

    return ALERT_CONTEXT_PROMPT.format(
        symbol=symbol,
        rule_name=rule_name,
        rule_type=rule_type,
        threshold=threshold,
        current_price=current_price,
        cost_basis_line=cost_basis_line,
        percent_change_line=percent_change_line,
        message=message,
    )
