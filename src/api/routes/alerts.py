"""Alerts API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_current_user, require_api_key
from src.core.alerts.models import AlertResponse
from src.core.alerts.repository import AlertRepository
from src.db.models import User

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/", response_model=List[AlertResponse])
def list_alerts(
    limit: int = Query(50, ge=1, le=500, description="Maximum alerts to return"),
    symbol: Optional[str] = None,
    rule_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List recent alerts with optional filters."""
    repo = AlertRepository(db)

    if symbol:
        return repo.get_by_symbol(symbol.upper(), user_id=user.id, limit=limit)
    if rule_id:
        return repo.get_by_rule(rule_id, user_id=user.id, limit=limit)

    return repo.get_recent(user_id=user.id, limit=limit)


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific alert by ID."""
    repo = AlertRepository(db)
    alert = repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    # Verify ownership
    if alert.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete an alert by ID."""
    repo = AlertRepository(db)
    # Verify ownership before deletion
    alert = repo.get_by_id(alert_id)
    if not alert or alert.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    repo.delete(alert_id)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def clear_alerts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Clear all alerts for the current user."""
    repo = AlertRepository(db)
    repo.clear_all(user_id=user.id)
