# Operations & Deployment Guide

This guide covers deployment, maintenance, and operational procedures for Signal Sentinel.

---

## Table of Contents

1. [Deployment](#deployment)
2. [Configuration](#configuration)
3. [Database Management](#database-management)
4. [Monitoring & Health](#monitoring--health)
5. [Key Rotation](#key-rotation)
6. [Backup & Recovery](#backup--recovery)
7. [Troubleshooting](#troubleshooting)

---

## Deployment

### Docker (Recommended)

#### Quick Start

```bash
# Clone and configure
git clone <repo>
cd intelligent_investing
cp .env.example .env
# Edit .env with your API keys

# Build and start
docker compose up -d

# Verify
docker compose ps
docker compose logs -f
```

#### Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| web | signal-sentinel-web | 8000 | API + Dashboard |
| worker | signal-sentinel-worker | - | Background monitor |

#### Redeploying

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d

# Verify
docker compose logs -f
```

#### Zero-Downtime Redeploy

```bash
# Rebuild without stopping
docker compose build

# Rolling restart
docker compose up -d --no-deps web
docker compose up -d --no-deps worker
```

### Manual Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Start API server
PYTHONPATH=. uvicorn src.api.app:app --host 0.0.0.0 --port 8000

# Start monitor worker (separate terminal)
PYTHONPATH=. python -m src.cli.main monitor start --interval 15
```

### Systemd Service (Linux)

Create `/etc/systemd/system/signal-sentinel-web.service`:

```ini
[Unit]
Description=Signal Sentinel Web
After=network.target

[Service]
Type=simple
User=signal-sentinel
WorkingDirectory=/opt/signal-sentinel
EnvironmentFile=/opt/signal-sentinel/.env
ExecStart=/opt/signal-sentinel/venv/bin/uvicorn src.api.app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable signal-sentinel-web
sudo systemctl start signal-sentinel-web
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | SQLite path (e.g., `sqlite:///./data/signal_sentinel.db`) |
| `SECRET_KEY` | Yes | JWT signing key (generate: `openssl rand -hex 32`) |
| `OPENAI_API_KEY` | No | For AI summaries |
| `TELEGRAM_BOT_TOKEN` | No | For Telegram notifications |
| `PLAID_CLIENT_ID` | No | For broker linking |
| `PLAID_SECRET` | No | For broker linking |
| `PLAID_ENV` | No | `sandbox`, `development`, or `production` |
| `ALPACA_API_KEY` | No | For Alpaca market data |
| `ALPACA_SECRET_KEY` | No | For Alpaca market data |
| `FINNHUB_API_KEY` | No | For Finnhub market data |

### Example .env

```bash
# Core
DATABASE_URL=sqlite:///./data/signal_sentinel.db
SECRET_KEY=your-super-secret-key-change-in-production

# AI (optional)
OPENAI_API_KEY=sk-...

# Notifications (optional)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...

# Market Data (optional - falls back to Yahoo Finance)
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
FINNHUB_API_KEY=...

# Broker Linking (optional)
PLAID_CLIENT_ID=...
PLAID_SECRET=...
PLAID_ENV=sandbox
```

---

## Database Management

### Location

By default: `./data/signal_sentinel.db` (SQLite)

### Manual Migrations

Signal Sentinel creates tables automatically on startup. For manual schema changes:

```bash
# Backup first!
cp data/signal_sentinel.db data/signal_sentinel.db.backup

# Access SQLite
sqlite3 data/signal_sentinel.db

# View schema
.schema

# Run custom SQL
sqlite> ALTER TABLE rules ADD COLUMN new_field TEXT;
```

### Adding Alembic (Future)

For proper migrations:

```bash
pip install alembic

# Initialize
alembic init migrations

# Generate migration
alembic revision --autogenerate -m "Add new_field to rules"

# Apply
alembic upgrade head
```

### Database Reset

```bash
# Stop services
docker compose down

# Backup and delete
mv data/signal_sentinel.db data/signal_sentinel.db.old

# Restart (tables recreated automatically)
docker compose up -d
```

---

## Monitoring & Health

### Health Check

```bash
# API health
curl http://localhost:8000/api/health

# Expected response
{
  "name": "Signal Sentinel",
  "version": "1.0.0",
  "status": "ok",
  "tagline": "Your AI-powered market watchdog."
}
```

### Container Status

```bash
# All services
docker compose ps

# Logs
docker compose logs -f
docker compose logs -f web
docker compose logs -f worker
```

### Monitor Status

Check when the monitor last ran:

```bash
# View recent alerts
PYTHONPATH=. python -m src.cli.main alerts list --limit 5

# View rules and last triggered
PYTHONPATH=. python -m src.cli.main rules list
```

### Common Health Indicators

| Check | Command | Healthy |
|-------|---------|---------|
| API up | `curl /api/health` | Status 200 |
| DB accessible | Check for recent alerts | Queries succeed |
| Monitor running | `docker compose logs worker` | Recent evaluation logs |
| Notifications working | `invest notifications test` | Telegram received |

---

## Key Rotation

### Rotating SECRET_KEY

1. Generate new key:
   ```bash
   openssl rand -hex 32
   ```

2. Update `.env`:
   ```
   SECRET_KEY=new-secret-key
   ```

3. Restart services:
   ```bash
   docker compose restart
   ```

**Note**: Rotating SECRET_KEY invalidates all existing JWT tokens. Users will need to log in again.

### Rotating API Keys

1. Generate new keys from providers (OpenAI, Alpaca, etc.)
2. Update `.env`
3. Restart services:
   ```bash
   docker compose restart
   ```

### Rotating User API Keys

Users can rotate their own API keys via:

```bash
# CLI
invest auth revoke-api-key OLD_KEY_ID
invest auth create-api-key "New Key Name"

# Or via API
DELETE /api/auth/api-keys/{key_id}
POST /api/auth/api-keys
```

---

## Backup & Recovery

### Backup Procedure

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/signal-sentinel"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_PATH="./data/signal_sentinel.db"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Stop worker to ensure clean backup
docker compose stop worker

# Backup database
cp "$DB_PATH" "$BACKUP_DIR/signal_sentinel_$TIMESTAMP.db"

# Backup .env (careful - contains secrets!)
cp .env "$BACKUP_DIR/env_$TIMESTAMP.bak"

# Restart worker
docker compose start worker

# Compress
gzip "$BACKUP_DIR/signal_sentinel_$TIMESTAMP.db"

# Clean old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.db.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/signal_sentinel_$TIMESTAMP.db.gz"
```

### Automated Backups (Cron)

```bash
# Edit crontab
crontab -e

# Daily backup at 3 AM
0 3 * * * /opt/signal-sentinel/backup.sh >> /var/log/signal-sentinel-backup.log 2>&1
```

### Recovery Procedure

```bash
# Stop services
docker compose down

# Restore database
gunzip /backups/signal-sentinel/signal_sentinel_YYYYMMDD_HHMMSS.db.gz
cp /backups/signal-sentinel/signal_sentinel_YYYYMMDD_HHMMSS.db ./data/signal_sentinel.db

# Restore .env if needed
cp /backups/signal-sentinel/env_YYYYMMDD_HHMMSS.bak .env

# Restart
docker compose up -d

# Verify
docker compose logs -f
```

### Off-site Backup

```bash
# Sync to remote storage
aws s3 sync /backups/signal-sentinel s3://my-bucket/signal-sentinel-backups/

# Or rsync to another server
rsync -avz /backups/signal-sentinel/ backup-server:/backups/signal-sentinel/
```

---

## Troubleshooting

### Common Issues

#### API Not Starting

```bash
# Check logs
docker compose logs web

# Common causes:
# - Missing .env file
# - Invalid DATABASE_URL
# - Port 8000 already in use
```

Fix port conflict:
```bash
# Find what's using port 8000
lsof -i :8000

# Or change port in docker-compose.yml
ports:
  - "8001:8000"
```

#### Worker Not Running Evaluations

```bash
# Check worker logs
docker compose logs worker

# Verify worker is healthy
docker compose ps

# Restart worker
docker compose restart worker
```

#### Telegram Notifications Not Sending

```bash
# Test manually
invest notifications test

# Verify config
invest notifications status

# Check bot token is valid
curl "https://api.telegram.org/bot<TOKEN>/getMe"
```

#### "No price data" Errors

```bash
# Check Yahoo Finance is accessible
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/AAPL" | jq .chart.result[0].meta.symbol

# Warrants need special handling
# IONQ/WS -> IONQ-WT
```

#### High Memory Usage

```bash
# Check container memory
docker stats

# Increase limits in docker-compose.yml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 512M
```

### Debug Mode

```bash
# Run with debug logging
LOG_LEVEL=DEBUG docker compose up

# Or for CLI
LOG_LEVEL=DEBUG PYTHONPATH=. python -m src.cli.main monitor run --verbose
```

### Database Issues

```bash
# Check database integrity
sqlite3 data/signal_sentinel.db "PRAGMA integrity_check;"

# Vacuum to optimize
sqlite3 data/signal_sentinel.db "VACUUM;"

# Check table sizes
sqlite3 data/signal_sentinel.db "SELECT name, COUNT(*) FROM sqlite_master GROUP BY name;"
```

---

## Maintenance Checklist

### Daily
- [ ] Check `/api/health` returns OK
- [ ] Verify recent alerts in dashboard
- [ ] Check worker logs for errors

### Weekly
- [ ] Review backup success
- [ ] Check disk space
- [ ] Review error logs
- [ ] Check rate limit hits (auth endpoints)

### Monthly
- [ ] Rotate API keys if policy requires
- [ ] Review and clean old alerts
- [ ] Database vacuum
- [ ] Update dependencies (`pip install --upgrade`)
- [ ] Review telemetry for usage patterns

### Quarterly
- [ ] Full backup test (restore to test environment)
- [ ] Security review
- [ ] Dependency audit (`pip-audit`)
- [ ] Performance review

---

*For user-facing documentation, see [Quickstart](./quickstart.md).*
