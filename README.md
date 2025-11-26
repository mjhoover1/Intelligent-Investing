# Signal Sentinel

**Your AI-powered watchdog for market signals**

Signal Sentinel is an automated, rule-driven portfolio monitoring system that watches your positions 24/7, evaluates technical and price-based conditions, and sends intelligent alerts with AI-powered context.

> You define the rules.
> Signal Sentinel does the watching.

## Core Features

- **Real-time portfolio monitoring** - Track all your holdings with live price data
- **AI-enhanced alerts** - Get notifications with concise AI summaries explaining why signals fired
- **Rule engine** - Price thresholds, RSI conditions, 52-week ranges, recovery zones, and more
- **Strategy presets** - One-click setups: swing trader, capital preservation, dip hunter...
- **Telegram notifications** - Instant alerts to your phone
- **Web dashboard** - Portfolio, rules, and alerts in one clean interface
- **Broker sync** - Import from Schwab CSV or sync automatically via Plaid
- **REST API** - Full API access for custom integrations
- **CLI** - Complete command-line interface
- **Docker deployable** - Easy containerized deployment
- **Multi-user authentication** - JWT tokens, API keys, user isolation

## Why Signal Sentinel?

Markets move fast.
You can't watch everything — but Signal Sentinel can.

With customizable guardrails, technical indicators, and intelligent summaries, you're always ahead of important movements without drowning in noise.

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/signal-sentinel.git
cd signal-sentinel

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### Basic Usage

```bash
# Add a position
invest portfolio add AAPL --shares 10 --cost-basis 150.00

# Create an alert rule
invest rules add "AAPL below $140" --ticker AAPL --type price_below --threshold 140

# Apply a strategy preset
invest strategies apply dip-hunter --tickers AAPL,MSFT,GOOGL

# Run monitoring
invest monitor once

# Start the web dashboard
uvicorn src.api.app:app --reload
# Visit http://localhost:8000
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `invest portfolio` | Manage portfolio holdings |
| `invest rules` | Create and manage alert rules |
| `invest alerts` | View triggered alerts |
| `invest strategies` | Apply strategy presets |
| `invest monitor` | Run monitoring cycles |
| `invest notifications` | Configure Telegram alerts |
| `invest brokers` | Manage broker integrations |
| `invest users` | User management |
| `invest version` | Show version info |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface                         │
│          (Web Dashboard / CLI / REST API)                   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Core Services                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Rule Engine │  │ AI Context  │  │ Alert Dispatcher    │ │
│  │             │  │ Generator   │  │ (Telegram/Email)    │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Portfolio   │  │ Market Data │  │ Broker Sync         │ │
│  │ Repository  │  │ (yfinance)  │  │ (Plaid/CSV)         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Rule Types

| Type | Description | Example |
|------|-------------|---------|
| `price_below` | Alert when price drops below threshold | "Alert if AAPL < $140" |
| `price_above` | Alert when price rises above threshold | "Alert if AAPL > $200" |
| `price_below_cost_pct` | Alert on % loss from cost basis | "Alert if any stock -20%" |
| `price_above_cost_pct` | Alert on % gain from cost basis | "Alert if any stock +50%" |
| `rsi_below` | Alert on oversold RSI | "Alert if RSI < 30" |
| `rsi_above` | Alert on overbought RSI | "Alert if RSI > 70" |
| `price_above_52w_high_pct` | Near 52-week high | "Alert if within 5% of high" |
| `price_below_52w_low_pct` | Near 52-week low | "Alert if within 5% of low" |
| `recovery_from_low_pct` | Bounce from lows | "Alert if +10% from low" |

## Strategy Presets

Pre-configured rule bundles for common use cases:

- **Dip Hunter** - Catch oversold opportunities (RSI < 30, recovery signals)
- **Swing Trader** - Track momentum reversals and breakouts
- **Capital Preservation** - Protective alerts for large drawdowns
- **Value Investor** - Near 52-week lows, deep discounts
- **Momentum Player** - Breakouts, new highs, strong RSI

## Configuration

Create a `.env` file with your settings:

```bash
# Required
API_KEY=your_secure_api_key

# Telegram (recommended)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# AI Summaries (optional)
OPENAI_API_KEY=your_openai_key

# Broker Sync (optional)
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=sandbox
```

## Legal Disclaimer

**This software is for informational and educational purposes only.**

- It does NOT provide financial advice
- It does NOT make buy/sell recommendations
- It does NOT execute any trades
- All alerts are based on rules YOU define
- Historical patterns are not guarantees of future performance

You are solely responsible for your investment decisions.

---

**Signal Sentinel** - Define the rules. We watch the market.

&copy; 2025 Signal Sentinel. All rights reserved.
