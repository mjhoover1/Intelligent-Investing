"""Alerts API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_current_user, require_api_key
from src.core.alerts.models import AlertResponse
from src.core.alerts.repository import AlertRepository
from src.db.models import User

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/", response_model=List[AlertResponse])
def list_alerts(
    limit: int = 50,
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
        return repo.get_by_rule(rule_id, limit=limit)

    return repo.get_recent(user_id=user.id, limit=limit)


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific alert by ID."""
    repo = AlertRepository(db)
    alert = repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: str,
    db: Session = Depends(get_db),
):
    """Delete an alert by ID."""
    repo = AlertRepository(db)
    deleted = repo.delete(alert_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )


@router.delete("/", status_code=status.HTTP_200_OK)
def clear_alerts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Clear all alerts for the current user."""
    repo = AlertRepository(db)
    count = repo.clear_all(user_id=user.id)
    return {"deleted": count}
