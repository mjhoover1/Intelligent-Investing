"""FastAPI application setup."""

from fastapi import FastAPI

from src.db.database import init_db
from src.api.routes import portfolio, rules, alerts, monitor

app = FastAPI(
    title="Intelligent Investing API",
    description="AI Portfolio Copilot - Rule-based portfolio monitoring with AI context",
    version="0.1.0",
)


@app.on_event("startup")
def startup():
    """Initialize database on startup."""
    init_db()


@app.get("/api/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Mount routers
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(rules.router, prefix="/api/rules", tags=["rules"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(monitor.router, prefix="/api/monitor", tags=["monitor"])
