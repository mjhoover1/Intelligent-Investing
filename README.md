# Intelligent Investing - AI Portfolio Copilot

An AI-driven portfolio monitoring system where **you define the rules** and the system watches your investments 24/7, alerting you when your criteria are met with contextual AI explanations.

## What This Is

This is a **rule-based portfolio monitoring engine** with AI-powered context and summarization. You set the criteria, and the system:

- Monitors your portfolio against your rules
- Sends alerts when conditions trigger
- Provides AI-generated context (historical patterns, news summaries, technical analysis)
- Helps you stay informed without constantly watching the markets

**This is NOT a robo-advisor or trading bot.** The system does not make decisions or execute trades. It provides facts, context, and education based on rules YOU define.

## Key Features

### User-Defined Rule Engine
- Create custom alert conditions: "Alert me if any stock drops 20% below my cost basis"
- Technical indicator triggers: RSI, MACD, moving average crossovers, volume spikes
- Portfolio-wide rules: "Alert if total portfolio drawdown exceeds 8% in 30 days"
- Combine multiple conditions with AND/OR logic

### Cost-Basis Aware Monitoring
- Track positions across multiple brokers
- Alerts relative to YOUR entry price, not just current price
- Understand your actual P&L position at all times

### AI-Powered Context (Not Advice)
- News summarization for your holdings
- Sentiment analysis of headlines
- Historical pattern recognition: "RSI < 30 historically correlates with oversold conditions"
- Technical analysis explanations in plain language

### Swing Detection Alerts
- Pattern recognition for potential swing tops/bottoms
- Volume divergence detection
- Multi-indicator confluence alerts
- Always presented as observations, not recommendations

### Multi-Channel Notifications
- Email alerts
- SMS notifications
- Discord/Telegram integration
- Webhook support for custom integrations

## Legal Disclaimer

**This software is for informational and educational purposes only.**

- It does NOT provide financial advice
- It does NOT make buy/sell recommendations
- It does NOT execute any trades
- All alerts are based on rules YOU define
- Historical patterns are not guarantees of future performance

You are solely responsible for your investment decisions. Consult a licensed financial advisor for personalized advice.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface                         │
│              (Dashboard / Rule Builder / Alerts)            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Core Services                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Rule Engine │  │ AI Context  │  │ Alert Dispatcher    │ │
│  │             │  │ Generator   │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Portfolio   │  │ Market Data │  │ News & Sentiment    │ │
│  │ Aggregator  │  │ Provider    │  │ Feeds               │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
intelligent_investing/
├── src/
│   ├── core/              # Core business logic
│   │   ├── rules/         # Rule engine and condition evaluators
│   │   ├── alerts/        # Alert generation and dispatch
│   │   └── portfolio/     # Portfolio management and tracking
│   ├── data/              # Data providers and aggregators
│   │   ├── market/        # Market data feeds (prices, indicators)
│   │   ├── news/          # News and sentiment data
│   │   └── brokers/       # Broker API integrations
│   ├── ai/                # AI/LLM integration layer
│   │   ├── context/       # Context generation for alerts
│   │   ├── summarization/ # News and analysis summarization
│   │   └── patterns/      # Pattern recognition helpers
│   ├── api/               # REST API endpoints
│   └── utils/             # Shared utilities
├── tests/                 # Test suite
├── config/                # Configuration files
├── docs/                  # Documentation
├── requirements.txt       # Python dependencies
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- API keys for market data (Alpaca, Finnhub, or similar)
- OpenAI API key (for AI context generation)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/intelligent_investing.git
cd intelligent_investing

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

1. Add your portfolio data (CSV import or broker API connection)
2. Define your rules in the rule builder
3. Configure notification channels
4. Start the monitoring service

## Example Rules

```python
# Alert if any position drops 20% below cost basis
{
    "name": "Cost Basis Protection",
    "condition": "position.current_price < position.cost_basis * 0.80",
    "alert": "{{symbol}} is now {{percent_change}}% below your cost basis"
}

# Swing top detection
{
    "name": "Potential Swing Top",
    "condition": "rsi > 70 AND macd_histogram < macd_histogram[-1] AND volume > avg_volume_20d * 1.5",
    "alert": "{{symbol}} showing potential swing top signals"
}

# News alert for large positions
{
    "name": "Major News Alert",
    "condition": "position.value > 2000 AND news.sentiment_change > 0.3",
    "alert": "Significant news for {{symbol}}: {{news.summary}}"
}
```

## Roadmap

### Phase 1: MVP (Personal Use)
- [ ] Manual portfolio import (CSV)
- [ ] Basic rule engine with price/percentage conditions
- [ ] Email notifications
- [ ] Simple AI context using OpenAI API

### Phase 2: Enhanced Intelligence
- [ ] Technical indicator library (RSI, MACD, Bollinger, etc.)
- [ ] News API integration with sentiment analysis
- [ ] Swing detection algorithms
- [ ] Dashboard UI

### Phase 3: SaaS Platform
- [ ] User authentication and accounts
- [ ] Multi-broker integration (Plaid, Alpaca)
- [ ] Advanced rule builder UI
- [ ] Subscription billing (Stripe)
- [ ] Mobile notifications

## Contributing

This project is currently in early development. Contributions welcome once the core architecture is established.

## License

MIT License - See LICENSE file for details.

---

**Remember:** This tool helps you stay informed. Your investment decisions are your own.
