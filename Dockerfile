# Signal Sentinel - Your AI-powered market watchdog
# Multi-stage build for smaller final image

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production image
FROM python:3.11-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY entrypoint.sh .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Create data directory for SQLite
RUN mkdir -p /app/data

# Environment variables (override in docker-compose or runtime)
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:///./data/signal_sentinel.db \
    LOG_LEVEL=INFO \
    MONITOR_INTERVAL_SECONDS=300

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health', timeout=5)" || exit 1

# Default entrypoint
ENTRYPOINT ["./entrypoint.sh"]

# Default command (can be overridden)
CMD ["web"]
