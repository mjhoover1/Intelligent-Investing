# Signal Sentinel Quickstart Guide

Get up and running with Signal Sentinel in 5 steps.

> **Important**: Signal Sentinel is an informational monitoring tool only. It does not provide financial advice. You are responsible for your own investment decisions.

---

## Step 1: Sign Up

### Web Dashboard (Recommended)

1. Navigate to `http://localhost:8000/onboarding`
2. Create an account with your email and password
3. You'll be guided through the onboarding wizard

### CLI Alternative

```bash
# Set up your environment
cp .env.example .env
# Edit .env with your API keys (OpenAI, etc.)

# Run the CLI
PYTHONPATH=. python3 -m src.cli.main --help
```

---

## Step 2: Import Holdings

You have three options to import your portfolio:

### Option A: Schwab CSV Export (Recommended)

1. Log into Schwab
2. Go to **Accounts** → **Positions**
3. Click **Export** (CSV format)
4. Upload the CSV in the onboarding wizard or via CLI:

```bash
invest portfolio import schwab-positions.csv
```

### Option B: Connect via Plaid (if configured)

1. Click "Connect Broker" in the onboarding wizard
2. Select your brokerage
3. Authorize the connection
4. Positions sync automatically

### Option C: Manual Entry

Add positions one at a time:

```bash
# CLI
invest portfolio add AAPL 100 --cost-basis 150.00

# Or use the web dashboard
```

**Verify your holdings:**
```bash
invest portfolio list
```

---

## Step 3: Apply a Strategy Preset

Strategy presets are pre-configured rule bundles. Choose one that matches your style:

| Strategy | Risk Level | Best For |
|----------|------------|----------|
| `capital-preservation` | Conservative | Protecting against losses |
| `swing-trader` | Medium | Capturing momentum swings |
| `dip-hunter` | Aggressive | Finding buying opportunities |
| `momentum-rider` | Aggressive | Riding strong uptrends |
| `long-term-holder` | Conservative | Buy-and-hold investors |
| `active-trader` | Medium | Hands-on management |

### Apply via Dashboard

1. Go to the **Strategies** section
2. Click **Apply** on your chosen strategy
3. Rules are created automatically

### Apply via CLI

```bash
# List available strategies
invest strategies list

# Apply a strategy
invest strategies apply swing-trader

# View your rules
invest rules list
```

---

## Step 4: Configure Telegram Notifications

Get instant alerts on your phone:

### 1. Get Your Telegram Chat ID

1. Open Telegram and search for `@userinfobot`
2. Start a chat with the bot
3. It will reply with your **Chat ID** (a number like `123456789`)

### 2. Create a Telegram Bot (Optional - for self-hosted)

If running your own instance:

1. Search for `@BotFather` on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the **Bot Token**
4. Add it to your `.env` file:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

### 3. Configure Your Chat ID

```bash
# CLI
invest notifications set-telegram YOUR_CHAT_ID

# Verify
invest notifications status
```

### 4. Send a Test Alert

```bash
invest notifications test
```

---

## Step 5: Start Monitoring & Rate Alerts

### Run the Monitor

The monitor checks your rules against current market data:

```bash
# One-time check
invest monitor run

# Run continuously (every 15 minutes)
invest monitor start --interval 15
```

### Using Docker (Production)

```bash
# Start everything
docker compose up -d

# View logs
docker compose logs -f worker
```

The worker container runs the monitor automatically on a schedule.

### Rate Your Alerts

Help Signal Sentinel learn which signals are useful:

```bash
# View recent alerts
invest alerts list

# Rate an alert
invest alerts rate ALERT_ID useful    # Signal was helpful
invest alerts rate ALERT_ID noise     # False positive / not helpful
invest alerts rate ALERT_ID actionable # Led to action
```

Rating alerts helps you track which rules and strategies actually work for your trading style.

---

## What's Next?

- **Customize rules**: Add your own rules beyond the presets
  ```bash
  invest rules add "My Custom Rule" price_below_cost_pct 15
  ```

- **View metrics**: Check signal quality over time at `/metrics`

- **API access**: Create API keys for programmatic access
  ```bash
  invest auth create-api-key "My Script"
  ```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `invest portfolio list` | View holdings |
| `invest portfolio add SYMBOL SHARES` | Add a position |
| `invest rules list` | View active rules |
| `invest rules add NAME TYPE THRESHOLD` | Create a rule |
| `invest strategies list` | View strategy presets |
| `invest strategies apply STRATEGY` | Apply a strategy |
| `invest monitor run` | Check rules once |
| `invest alerts list` | View recent alerts |
| `invest alerts rate ID RATING` | Rate an alert |

---

## Troubleshooting

### "No price data" for a symbol
- Check if the symbol is valid on Yahoo Finance
- Warrants use `-WT` suffix (e.g., `IONQ-WT`)

### Alerts not sending to Telegram
- Verify your chat ID: `invest notifications status`
- Check bot token in `.env`
- Ensure you've started a chat with your bot

### Rules not triggering
- Verify rules are enabled: `invest rules list`
- Check cooldown periods (rules won't re-trigger during cooldown)
- Run `invest monitor run --verbose` for detailed output

---

*Questions? Check the [Rule Types Guide](./rule-types.md) or [Strategy Presets](./strategies.md).*
