"""Strategy presets API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_current_user, require_api_key
from src.core.strategies import list_presets, get_preset
from src.core.rules.repository import RuleRepository
from src.db.models import Rule, User

router = APIRouter(prefix="/strategies", dependencies=[Depends(require_api_key)])


def _escape_like_pattern(value: str) -> str:
    """Escape special characters in LIKE patterns.

    Args:
        value: String to escape

    Returns:
        Escaped string safe for LIKE patterns
    """
    # Escape backslash first, then other special chars
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class RuleTemplateResponse(BaseModel):
    """Rule template in a strategy."""

    name: str
    rule_type: str
    threshold: float
    symbol: Optional[str]
    cooldown_minutes: int
    description: str


class StrategyResponse(BaseModel):
    """Strategy preset response."""

    id: str
    name: str
    description: str
    category: str
    risk_level: str
    rules: List[RuleTemplateResponse]


class StrategyApplyResponse(BaseModel):
    """Response from applying a strategy."""

    status: str
    strategy_id: str
    strategy_name: str
    rules_created: int
    rule_ids: List[str]


@router.get("/", response_model=List[StrategyResponse])
def list_all_strategies():
    """List all available strategy presets."""
    presets = list_presets()

    return [
        StrategyResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            category=p.category,
            risk_level=p.risk_level,
            rules=[
                RuleTemplateResponse(
                    name=r.name,
                    rule_type=r.rule_type.value,
                    threshold=r.threshold,
                    symbol=r.symbol,
                    cooldown_minutes=r.cooldown_minutes,
                    description=r.description,
                )
                for r in p.rules
            ],
        )
        for p in presets
    ]


@router.get("/{strategy_id}", response_model=StrategyResponse)
def get_strategy(strategy_id: str):
    """Get a specific strategy preset."""
    preset = get_preset(strategy_id)

    if not preset:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")

    return StrategyResponse(
        id=preset.id,
        name=preset.name,
        description=preset.description,
        category=preset.category,
        risk_level=preset.risk_level,
        rules=[
            RuleTemplateResponse(
                name=r.name,
                rule_type=r.rule_type.value,
                threshold=r.threshold,
                symbol=r.symbol,
                cooldown_minutes=r.cooldown_minutes,
                description=r.description,
            )
            for r in preset.rules
        ],
    )


@router.post("/{strategy_id}/apply", response_model=StrategyApplyResponse)
def apply_strategy(
    strategy_id: str,
    replace: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Apply a strategy preset, creating all its rules.

    Args:
        strategy_id: Strategy preset ID
        replace: If True, remove existing rules from this strategy first
    """
    preset = get_preset(strategy_id)

    if not preset:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")

    repo = RuleRepository(db)

    # Check for existing rules from this strategy
    escaped_id = _escape_like_pattern(preset.id)
    existing = db.query(Rule).filter(
        Rule.user_id == user.id,
        Rule.name.like(f"[{escaped_id}]%", escape="\\")
    ).all()

    if existing and not replace:
        raise HTTPException(
            status_code=409,
            detail=f"Strategy already has {len(existing)} rules. Use replace=true to overwrite.",
        )

    # Remove existing if replacing
    if replace and existing:
        for rule in existing:
            db.delete(rule)
        db.flush()  # Ensure deletions are applied before creating new rules

    # Create new rules
    created_rules = []
    for rule_template in preset.rules:
        rule = repo.create(
            name=rule_template.name,
            rule_type=rule_template.rule_type,
            threshold=rule_template.threshold,
            symbol=rule_template.symbol,
            enabled=True,
            cooldown_minutes=rule_template.cooldown_minutes,
            user_id=user.id,
        )
        created_rules.append(rule)

    return StrategyApplyResponse(
        status="ok",
        strategy_id=preset.id,
        strategy_name=preset.name,
        rules_created=len(created_rules),
        rule_ids=[r.id for r in created_rules],
    )


@router.delete("/{strategy_id}")
def remove_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove all rules from a strategy preset."""
    preset = get_preset(strategy_id)

    if not preset:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")

    # Find existing rules from this strategy
    escaped_id = _escape_like_pattern(preset.id)
    existing = db.query(Rule).filter(
        Rule.user_id == user.id,
        Rule.name.like(f"[{escaped_id}]%", escape="\\")
    ).all()

    if not existing:
        return {"status": "ok", "message": "No rules to remove", "removed": 0}

    for rule in existing:
        db.delete(rule)
    db.flush()

    return {"status": "ok", "removed": len(existing)}
