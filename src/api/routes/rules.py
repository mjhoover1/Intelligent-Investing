"""Rules API routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_current_user, require_api_key
from src.core.rules.models import RuleCreate, RuleUpdate, RuleResponse
from src.core.rules.repository import RuleRepository
from src.db.models import User

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/", response_model=List[RuleResponse])
def list_rules(
    active_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all rules for the current user."""
    repo = RuleRepository(db)
    if active_only:
        return repo.get_active(user_id=user.id)
    return repo.get_all(user_id=user.id)


@router.post("/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def add_rule(
    payload: RuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new rule."""
    repo = RuleRepository(db)

    # Check if name already exists
    existing = repo.get_by_name(payload.name, user_id=user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rule named '{payload.name}' already exists",
        )

    rule = repo.create(
        name=payload.name,
        rule_type=payload.rule_type,
        threshold=payload.threshold,
        symbol=payload.symbol,
        enabled=payload.enabled,
        cooldown_minutes=payload.cooldown_minutes,
        user_id=user.id,
    )
    return rule


@router.get("/{rule_id}", response_model=RuleResponse)
def get_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific rule by ID."""
    repo = RuleRepository(db)
    rule = repo.get_by_id(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )
    # Verify ownership
    if rule.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )
    return rule


@router.patch("/{rule_id}", response_model=RuleResponse)
def update_rule(
    rule_id: str,
    payload: RuleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a rule."""
    repo = RuleRepository(db)
    rule = repo.get_by_id(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )
    # Verify ownership
    if rule.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )

    # Check for name conflict
    if payload.name and payload.name != rule.name:
        existing = repo.get_by_name(payload.name, user_id=user.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Rule named '{payload.name}' already exists",
            )

    updated = repo.update(
        rule_id=rule_id,
        name=payload.name,
        threshold=payload.threshold,
        symbol=payload.symbol,
        enabled=payload.enabled,
        cooldown_minutes=payload.cooldown_minutes,
    )
    return updated


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a rule by ID."""
    repo = RuleRepository(db)
    # Verify ownership before deletion
    rule = repo.get_by_id(rule_id)
    if not rule or rule.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )
    repo.delete(rule_id)


@router.post("/{rule_id}/enable", response_model=RuleResponse)
def enable_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Enable a rule."""
    repo = RuleRepository(db)
    # Verify ownership
    rule = repo.get_by_id(rule_id)
    if not rule or rule.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )
    updated = repo.update(rule_id, enabled=True)
    return updated


@router.post("/{rule_id}/disable", response_model=RuleResponse)
def disable_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Disable a rule."""
    repo = RuleRepository(db)
    # Verify ownership
    rule = repo.get_by_id(rule_id)
    if not rule or rule.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )
    updated = repo.update(rule_id, enabled=False)
    return updated
