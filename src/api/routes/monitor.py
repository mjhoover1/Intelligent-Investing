"""Monitor API routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_current_user, require_api_key
from src.core.monitor import run_monitor_cycle
from src.db.models import User

router = APIRouter(dependencies=[Depends(require_api_key)])


class MonitorRunResponse(BaseModel):
    """Response from running a monitor cycle."""

    status: str
    alerts_created: int
    alert_ids: List[str]


class MonitorStatusResponse(BaseModel):
    """Current monitoring status."""

    holdings_count: int
    rules_count: int
    active_rules_count: int
    default_interval_seconds: int


@router.post("/run", response_model=MonitorRunResponse)
def run_monitor(
    ai: bool = False,
    ignore_cooldown: bool = False,
):
    """Run a single monitoring cycle.

    Args:
        ai: Generate AI context for alerts
        ignore_cooldown: Ignore rule cooldowns

    Note: Returns alert IDs. Use GET /api/alerts/ to fetch full alert details.
    """
    alerts = run_monitor_cycle(use_ai=ai, ignore_cooldown=ignore_cooldown)

    # Extract IDs while session is still valid (run_monitor_cycle handles its own session)
    # The alerts returned have .id accessible even after session close
    alert_ids = [str(a.id) for a in alerts]

    return MonitorRunResponse(
        status="ok",
        alerts_created=len(alerts),
        alert_ids=alert_ids,
    )


@router.get("/status", response_model=MonitorStatusResponse)
def get_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current monitoring status."""
    from src.core.portfolio.repository import HoldingRepository
    from src.core.rules.repository import RuleRepository
    from src.config import get_settings

    settings = get_settings()

    holding_repo = HoldingRepository(db)
    rule_repo = RuleRepository(db)

    holdings = holding_repo.get_all(user_id=user.id)
    rules = rule_repo.get_all(user_id=user.id)
    active_rules = rule_repo.get_active(user_id=user.id)

    return MonitorStatusResponse(
        holdings_count=len(holdings),
        rules_count=len(rules),
        active_rules_count=len(active_rules),
        default_interval_seconds=settings.monitor_interval_seconds,
    )
