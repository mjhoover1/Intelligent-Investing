"""Web dashboard routes."""

from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_current_user
from src.db.models import Alert, Holding, Rule
from src.data.market.provider import market_data

router = APIRouter()

# Set up templates
templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Render the main dashboard."""
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

    # Sort by market value descending
    holdings_data.sort(key=lambda x: x["market_value"] or 0, reverse=True)

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

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "holdings": holdings_data,
            "rules": rules_data,
            "alerts": alerts_db,
            "total_value": total_value,
            "total_cost": total_cost,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
        },
    )
