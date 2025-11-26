"""FastAPI application setup."""

from fastapi import FastAPI

from src.db.database import init_db
from src.api.routes import portfolio, rules, alerts, monitor, web, strategies, auth, brokers
from src.config import PRODUCT_NAME, PRODUCT_TAGLINE, PRODUCT_VERSION, PRODUCT_DESCRIPTION

app = FastAPI(
    title=f"{PRODUCT_NAME} API",
    description=PRODUCT_DESCRIPTION,
    version=PRODUCT_VERSION,
)


@app.on_event("startup")
def startup():
    """Initialize database on startup."""
    init_db()


@app.get("/api/health")
def health():
    """Health check endpoint."""
    return {
        "name": PRODUCT_NAME,
        "version": PRODUCT_VERSION,
        "status": "ok",
        "tagline": PRODUCT_TAGLINE,
    }


# Mount API routers
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(rules.router, prefix="/api/rules", tags=["rules"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(monitor.router, prefix="/api/monitor", tags=["monitor"])
app.include_router(strategies.router, prefix="/api", tags=["strategies"])
app.include_router(brokers.router, prefix="/api", tags=["brokers"])

# Mount web dashboard (no prefix - serves at root)
app.include_router(web.router, tags=["dashboard"])
