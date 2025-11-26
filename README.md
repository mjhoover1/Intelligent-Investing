# Signal Sentinel

**Your AI-powered watchdog for market signals**

Signal Sentinel is an automated, rule-driven portfolio monitoring system that watches your positions 24/7, evaluates technical and price-based conditions, and sends intelligent alerts with AI-powered context.

> You define the rules.
> Signal Sentinel does the watching.

## Core Features

- **Real-time portfolio monitoring** - Track all your holdings with live price data from Yahoo Finance
- **AI-enhanced alerts** - Get notifications with concise AI summaries explaining why signals fired
- **Flexible rule engine** - Price thresholds, percentage changes, RSI conditions, and more
- **Strategy presets** - One-click rule bundles: Capital Preservation, Swing Trader, Dip Hunter...
- **Telegram notifications** - Instant alerts delivered to your phone
- **Web dashboard** - Portfolio overview, rules management, and alert history in a clean interface
- **Guided onboarding** - Step-by-step setup for new users
- **Broker sync** - Import from Schwab CSV or sync automatically via Plaid
- **REST API** - Full programmatic access for custom integrations
- **CLI** - Complete command-line interface for power users
- **Multi-user authentication** - JWT tokens, API keys, and user isolation
- **Signal quality metrics** - Track which rules are useful vs. noise
- **Docker deployable** - Easy containerized deployment

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

# Initialize database
python -m src.cli.main version
```

### Basic Usage

```bash
# Add a position
invest portfolio add AAPL 10 150.00

# Create an alert rule (alert if AAPL drops 15% below cost)
invest rules add "AAPL Loss Alert" price_below_cost_pct -15 --symbol AAPL

# Create a global rule (alert if any stock drops 20%)
invest rules add "Portfolio Protection" price_below_cost_pct -20

# Apply a strategy preset
invest strategies apply dip-hunter

# Run a single monitoring cycle
invest monitor run

# Start continuous monitoring
invest monitor start --interval 300

# Start the web dashboard
uvicorn src.api.app:app --reload
# Visit http://localhost:8000
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `invest portfolio` | Manage portfolio holdings (add, list, update, remove, import, export) |
| `invest rules` | Create and manage alert rules |
| `invest alerts` | View alert history and provide feedback |
| `invest strategies` | Apply pre-built strategy presets |
| `invest monitor` | Run monitoring cycles (single or continuous) |
| `invest notifications` | Configure Telegram notifications |
| `invest brokers` | Manage broker integrations (Plaid) |
| `invest users` | User management and authentication |
| `invest version` | Show version info |

### Portfolio Commands

```bash
# Add a holding
invest portfolio add SYMBOL SHARES COST_BASIS [--date YYYY-MM-DD]

# List all holdings
invest portfolio list

# Show portfolio value with P&L
invest portfolio value

# Get current price
invest portfolio price AAPL

# Import from Schwab CSV
invest portfolio import-schwab positions.csv [--mode upsert|replace|add_only]

# Export to CSV
invest portfolio export --output portfolio.csv
```

### Rule Commands

```bash
# Add a rule
invest rules add "Rule Name" RULE_TYPE THRESHOLD [--symbol SYMBOL] [--cooldown MINUTES]

# List all rules
invest rules list

# List available rule types
invest rules types

# Evaluate rules without creating alerts
invest rules evaluate

# Enable/disable rules
invest rules enable "Rule Name"
invest rules disable "Rule Name"

# Remove a rule
invest rules remove "Rule Name"
```

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
│  │             │  │ Generator   │  │ (Telegram/Console)  │ │
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

| Type | Description | Example Threshold |
|------|-------------|-------------------|
| `price_below_cost_pct` | Alert on % loss from cost basis | `-20` (alert at 20% loss) |
| `price_above_cost_pct` | Alert on % gain from cost basis | `50` (alert at 50% gain) |
| `price_below_value` | Alert when price drops below $ value | `140` (alert if < $140) |
| `price_above_value` | Alert when price rises above $ value | `200` (alert if > $200) |
| `rsi_below_value` | Alert on oversold RSI (14-period) | `30` (alert if RSI < 30) |
| `rsi_above_value` | Alert on overbought RSI (14-period) | `70` (alert if RSI > 70) |

## Strategy Presets

Pre-configured rule bundles for common investment styles:

| Preset | Category | Risk | Description |
|--------|----------|------|-------------|
| `capital-preservation` | Protection | Conservative | Protect from significant drawdowns (-15%, -25%, -35%) |
| `swing-trader` | Profit | Medium | Capture momentum swings with RSI and profit targets |
| `dip-hunter` | Opportunity | Aggressive | Find oversold opportunities (RSI < 30, -20% dips) |
| `momentum-rider` | Profit | Aggressive | Ride uptrends, exit before reversals |
| `recovery-tracker` | Balanced | Conservative | Track underwater positions recovering |
| `long-term-holder` | Balanced | Conservative | Minimal alerts for buy-and-hold investors |
| `active-trader` | Balanced | Medium | Comprehensive alerts for hands-on management |

```bash
# View available strategies
invest strategies list

# See strategy details
invest strategies show dip-hunter

# Apply a strategy
invest strategies apply dip-hunter

# Remove strategy rules
invest strategies remove dip-hunter
```

## Web Dashboard

The web interface provides:

- **Dashboard** - Portfolio overview with current values and P&L
- **Holdings** - View and manage positions
- **Rules** - Create, edit, enable/disable alert rules
- **Alerts** - View triggered alerts with AI summaries
- **Onboarding** - Guided setup for new users

Start the dashboard:
```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

## Configuration

Create a `.env` file with your settings:

```bash
# Required for API access
API_KEY=your_secure_api_key_here

# Database (default: SQLite)
DATABASE_URL=sqlite:///./data/signal_sentinel.db

# Monitoring settings
MONITOR_INTERVAL_SECONDS=300
PRICE_CACHE_SECONDS=60

# Telegram notifications (recommended)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# AI Summaries (optional, requires OpenAI)
OPENAI_API_KEY=your_openai_key

# Broker Sync via Plaid (optional)
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=sandbox
```

### Setting up Telegram

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the token to `TELEGRAM_BOT_TOKEN` in `.env`
4. Send any message to your new bot
5. Run: `invest notifications telegram-get-chat-id`
6. Copy the chat ID to `TELEGRAM_CHAT_ID` in `.env`
7. Test: `invest notifications test --telegram`

## API Reference

The REST API is available at `/api/v1/` with the following endpoints:

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/api/v1/portfolio` | GET, POST | List/add holdings |
| `/api/v1/portfolio/{symbol}` | GET, PATCH, DELETE | Manage specific holding |
| `/api/v1/rules` | GET, POST | List/add rules |
| `/api/v1/rules/{id}` | GET, PATCH, DELETE | Manage specific rule |
| `/api/v1/alerts` | GET, DELETE | List/clear alerts |
| `/api/v1/brokers` | GET | Broker integration status |

Authentication: Include `X-API-Key: your_api_key` header.

## Docker Deployment

```bash
# Build the image
docker build -t signal-sentinel .

# Run with environment file
docker run -d \
  --name signal-sentinel \
  -p 8000:8000 \
  --env-file .env \
  -v ./data:/app/data \
  signal-sentinel
```

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Type checking
mypy src/

# Format code
black src/ tests/
```

## Legal Disclaimer

**This software is for informational and educational purposes only.**

- It does NOT provide financial advice
- It does NOT make buy/sell recommendations
- It does NOT execute any trades
- All alerts are based on rules YOU define
- Historical patterns are not guarantees of future performance
- Market data is provided by Yahoo Finance and may be delayed

You are solely responsible for your investment decisions. Always do your own research and consider consulting a qualified financial advisor.

---

**Signal Sentinel** - Define the rules. We watch the market.

&copy; 2025 Signal Sentinel. All rights reserved.
