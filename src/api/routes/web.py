"""Web dashboard routes."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_web_user
from src.db.models import Alert, Holding, Rule, User
from src.data.market.provider import market_data
from src.core.strategies import list_presets, get_preset
from src.core.rules.repository import RuleRepository
from src.core.metrics import MetricsService

router = APIRouter()


def _escape_like_pattern(value: str) -> str:
    """Escape special characters in LIKE patterns."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

# Set up templates
templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/landing", response_class=HTMLResponse)
def landing(request: Request):
    """Render the marketing landing page."""
    return templates.TemplateResponse("landing.html", {"request": request})


@router.get("/terms", response_class=HTMLResponse)
def terms_of_service(request: Request):
    """Render the Terms of Service page."""
    return templates.TemplateResponse("legal.html", {"request": request, "page": "terms"})


@router.get("/privacy", response_class=HTMLResponse)
def privacy_policy(request: Request):
    """Render the Privacy Policy page."""
    return templates.TemplateResponse("legal.html", {"request": request, "page": "privacy"})


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_web_user),
):
    """Render the main dashboard."""
    # Redirect to onboarding if not authenticated or onboarding incomplete
    if not user:
        return RedirectResponse(url="/onboarding", status_code=303)

    if not user.onboarding_completed_at:
        return RedirectResponse(url=f"/onboarding?step={user.onboarding_step}", status_code=303)

    # Get holdings with current prices
    holdings_db: List[Holding] = (
        db.query(Holding).filter(Holding.user_id == user.id).all()
    )

    # Fetch current prices for all holdings
    symbols = [h.symbol for h in holdings_db]
    prices = market_data.get_prices(symbols, db)

    # Build holdings data with P&L calculations
    holdings_data = []
    total_value = 0.0
    total_cost = 0.0

    for h in holdings_db:
        current_price = prices.get(h.symbol)
        market_value = None
        pnl = None
        pnl_pct = None

        if current_price:
            market_value = current_price * h.shares
            cost_total = h.cost_basis * h.shares
            pnl = market_value - cost_total
            pnl_pct = (pnl / cost_total * 100) if cost_total > 0 else 0

            total_value += market_value
            total_cost += cost_total

        holdings_data.append({
            "symbol": h.symbol,
            "shares": h.shares,
            "cost_basis": h.cost_basis,
            "current_price": current_price,
            "market_value": market_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })

    # Filter out holdings with no price data (shouldn't happen often now that
    # warrant symbols like IONQ/WS are normalized to Yahoo's -WT format)
    holdings_with_prices = [h for h in holdings_data if h["current_price"] is not None]
    holdings_without_prices = [h for h in holdings_data if h["current_price"] is None]

    # Sort by market value descending
    holdings_with_prices.sort(key=lambda x: x["market_value"] or 0, reverse=True)

    # Calculate portfolio totals
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    # Get rules
    rules_db: List[Rule] = (
        db.query(Rule).filter(Rule.user_id == user.id).all()
    )
    rules_data = [
        {
            "name": r.name,
            "rule_type": r.rule_type,
            "symbol": r.symbol,
            "threshold": r.threshold,
            "enabled": r.enabled,
            "cooldown_minutes": r.cooldown_minutes,
        }
        for r in rules_db
    ]

    # Get recent alerts (last 20)
    alerts_db: List[Alert] = (
        db.query(Alert)
        .filter(Alert.user_id == user.id)
        .order_by(Alert.triggered_at.desc())
        .limit(20)
        .all()
    )

    # Get strategy presets and check which are active
    strategies = list_presets()
    active_strategies = set()
    for preset in strategies:
        escaped_id = _escape_like_pattern(preset.id)
        count = db.query(Rule).filter(
            Rule.user_id == user.id,
            Rule.name.like(f"[{escaped_id}]%", escape="\\"),
        ).count()
        if count > 0:
            active_strategies.add(preset.id)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "holdings": holdings_with_prices,
            "holdings_no_price": holdings_without_prices,
            "rules": rules_data,
            "alerts": alerts_db,
            "total_value": total_value,
            "total_cost": total_cost,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "strategies": strategies,
            "active_strategies": active_strategies,
        },
    )


@router.post("/strategies/{strategy_id}/apply")
def apply_strategy_from_dashboard(
    request: Request,
    strategy_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_web_user),
):
    """Apply a strategy preset from the dashboard."""
    if not user:
        return RedirectResponse(url="/onboarding", status_code=303)

    preset = get_preset(strategy_id)

    if not preset:
        return RedirectResponse(url="/", status_code=303)

    repo = RuleRepository(db)

    # Check for existing rules from this strategy
    escaped_id = _escape_like_pattern(preset.id)
    existing = db.query(Rule).filter(
        Rule.user_id == user.id,
        Rule.name.like(f"[{escaped_id}]%", escape="\\")
    ).all()

    # Skip if already applied
    if existing:
        return RedirectResponse(url="/", status_code=303)

    # Create new rules
    for rule_template in preset.rules:
        repo.create(
            name=rule_template.name,
            rule_type=rule_template.rule_type,
            threshold=rule_template.threshold,
            symbol=rule_template.symbol,
            enabled=True,
            cooldown_minutes=rule_template.cooldown_minutes,
            user_id=user.id,
        )

    return RedirectResponse(url="/", status_code=303)


@router.get("/metrics", response_class=HTMLResponse)
def metrics_page(
    request: Request,
    period: int = 30,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_web_user),
):
    """Render the signal performance metrics page."""
    if not user:
        return RedirectResponse(url="/onboarding", status_code=303)

    if not user.onboarding_completed_at:
        return RedirectResponse(url=f"/onboarding?step={user.onboarding_step}", status_code=303)

    # Get metrics summary
    metrics_service = MetricsService(db)
    summary = metrics_service.get_summary(user.id, period)

    return templates.TemplateResponse(
        "metrics.html",
        {
            "request": request,
            "period": period,
            "summary": summary,
            "user_metrics": summary.user_metrics,
            "rule_metrics": summary.rule_metrics,
            "asset_metrics": summary.asset_metrics,
        },
    )
