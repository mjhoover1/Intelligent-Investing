"""Onboarding flow routes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.core.auth import get_auth_service
from src.core.brokers import plaid_provider
from src.core.portfolio.importers import import_schwab_csv
from src.core.portfolio.repository import HoldingRepository
from src.core.rules.repository import RuleRepository
from src.core.strategies import list_presets, get_preset
from src.db.models import Holding, User

router = APIRouter()

templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


def get_session_user(request: Request, db: Session) -> Optional[User]:
    """Get user from session cookie if exists.

    Uses JWT access_token for secure validation, not raw user_id.
    """
    from src.core.auth.security import decode_access_token

    # Validate via JWT token (secure)
    access_token = request.cookies.get("access_token")
    if access_token:
        payload = decode_access_token(access_token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.is_active:
                    return user
    return None


@router.get("/onboarding", response_class=HTMLResponse)
def onboarding_page(
    request: Request,
    step: int = 1,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Render the onboarding wizard."""
    user = get_session_user(request, db)

    # Determine current step
    if user:
        # If user completed onboarding, redirect to dashboard
        if user.onboarding_completed_at:
            return RedirectResponse(url="/", status_code=303)
        # Use requested step if valid (user might navigate back)
        current_step = max(2, min(step, 4))  # Steps 2-4 for logged in users
    else:
        current_step = 1  # Must start at step 1 if not logged in

    # Get data for current step
    context = {
        "request": request,
        "step": current_step,
        "error": error,
        "plaid_configured": plaid_provider.is_configured(),
        "holdings_count": 0,
        "strategies": [],
    }

    if user and current_step >= 2:
        context["holdings_count"] = db.query(Holding).filter(
            Holding.user_id == user.id
        ).count()

    if current_step == 3:
        context["strategies"] = list_presets()

    return templates.TemplateResponse("onboarding.html", context)


@router.post("/onboarding/register")
def onboarding_register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle registration from onboarding."""
    # Validate passwords match
    if password != password_confirm:
        return templates.TemplateResponse(
            "onboarding.html",
            {"request": request, "step": 1, "error": "Passwords do not match"},
        )

    if len(password) < 8:
        return templates.TemplateResponse(
            "onboarding.html",
            {"request": request, "step": 1, "error": "Password must be at least 8 characters"},
        )

    auth_service = get_auth_service(db)

    try:
        user, token = auth_service.register(email=email, password=password)
        # Update onboarding step
        user.onboarding_step = 2
        db.commit()

        # Set session cookie and redirect to step 2
        response = RedirectResponse(url="/onboarding?step=2", status_code=303)
        response.set_cookie(
            key="user_id",
            value=user.id,
            httponly=True,
            max_age=86400 * 7,  # 7 days
            samesite="lax",
        )
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=86400 * 7,
            samesite="lax",
        )
        return response

    except ValueError as e:
        return templates.TemplateResponse(
            "onboarding.html",
            {"request": request, "step": 1, "error": str(e)},
        )


@router.post("/onboarding/login")
def onboarding_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle login from onboarding."""
    auth_service = get_auth_service(db)

    try:
        user, token = auth_service.login(email=email, password=password)

        # Determine which step to go to
        if user.onboarding_completed_at:
            redirect_url = "/"
        else:
            redirect_url = f"/onboarding?step={user.onboarding_step}"

        response = RedirectResponse(url=redirect_url, status_code=303)
        response.set_cookie(
            key="user_id",
            value=user.id,
            httponly=True,
            max_age=86400 * 7,
            samesite="lax",
        )
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=86400 * 7,
            samesite="lax",
        )
        return response

    except ValueError as e:
        return templates.TemplateResponse(
            "onboarding.html",
            {"request": request, "step": 1, "error": str(e)},
        )


@router.post("/onboarding/import/csv")
async def onboarding_import_csv(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Handle CSV import during onboarding."""
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse(url="/onboarding", status_code=303)

    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
        result = import_schwab_csv(db, user.id, csv_content, mode="upsert")

        # Update onboarding step
        user.onboarding_step = 3
        db.commit()

        return RedirectResponse(url="/onboarding?step=3", status_code=303)

    except Exception as e:
        return templates.TemplateResponse(
            "onboarding.html",
            {
                "request": request,
                "step": 2,
                "error": f"Failed to import CSV: {str(e)}",
                "plaid_configured": plaid_provider.is_configured(),
                "holdings_count": 0,
                "strategies": [],
            },
        )


@router.post("/onboarding/import/manual")
def onboarding_import_manual(
    request: Request,
    symbol: str = Form(...),
    shares: float = Form(...),
    cost_basis: float = Form(...),
    action: str = Form("add_more"),
    db: Session = Depends(get_db),
):
    """Handle manual position add during onboarding."""
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse(url="/onboarding", status_code=303)

    # Validate positive values
    if shares <= 0 or cost_basis <= 0:
        holdings_count = db.query(Holding).filter(Holding.user_id == user.id).count()
        return templates.TemplateResponse(
            "onboarding.html",
            {
                "request": request,
                "step": 2,
                "error": "Shares and cost basis must be positive numbers",
                "holdings_count": holdings_count,
            },
        )

    repo = HoldingRepository(db)

    # Check if symbol already exists
    existing = repo.get_by_symbol(symbol.upper(), user_id=user.id)
    if existing:
        # Update existing
        repo.update(
            holding_id=existing.id,
            shares=shares,
            cost_basis=cost_basis,
        )
    else:
        # Create new
        repo.create(
            symbol=symbol.upper(),
            shares=shares,
            cost_basis=cost_basis,
            user_id=user.id,
        )

    db.commit()

    # Determine next action
    if action == "done":
        user.onboarding_step = 3
        db.commit()
        return RedirectResponse(url="/onboarding?step=3", status_code=303)
    else:
        # Stay on step 2 to add more
        holdings_count = db.query(Holding).filter(Holding.user_id == user.id).count()
        return templates.TemplateResponse(
            "onboarding.html",
            {
                "request": request,
                "step": 2,
                "plaid_configured": plaid_provider.is_configured(),
                "holdings_count": holdings_count,
                "strategies": [],
            },
        )


@router.post("/onboarding/strategy/{strategy_id}")
def onboarding_apply_strategy(
    strategy_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Apply a strategy preset during onboarding."""
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse(url="/onboarding", status_code=303)

    preset = get_preset(strategy_id)
    if not preset:
        return RedirectResponse(url="/onboarding?step=3", status_code=303)

    repo = RuleRepository(db)

    # Create rules from preset
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

    # Update onboarding step
    user.onboarding_step = 4
    db.commit()

    return RedirectResponse(url="/onboarding?step=4", status_code=303)


@router.post("/onboarding/complete")
def onboarding_complete(
    request: Request,
    db: Session = Depends(get_db),
):
    """Mark onboarding as complete."""
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse(url="/onboarding", status_code=303)

    user.onboarding_completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
def logout():
    """Log out and clear session."""
    response = RedirectResponse(url="/onboarding", status_code=303)
    response.delete_cookie("user_id")
    response.delete_cookie("access_token")
    return response
