"""FastAPI application setup."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.db.database import init_db
from src.api.routes import portfolio, rules, alerts, monitor, web, strategies, auth, brokers, onboarding, metrics
from src.config import PRODUCT_NAME, PRODUCT_TAGLINE, PRODUCT_VERSION, PRODUCT_DESCRIPTION

# Rate limiter - key by IP address
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=f"{PRODUCT_NAME} API",
    description=PRODUCT_DESCRIPTION,
    version=PRODUCT_VERSION,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


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
app.include_router(metrics.router, prefix="/api", tags=["metrics"])

# Mount onboarding flow (no prefix - serves at root)
app.include_router(onboarding.router, tags=["onboarding"])

# Mount web dashboard (no prefix - serves at root)
app.include_router(web.router, tags=["dashboard"])
