"""Portfolio API routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_current_user, require_api_key
from src.core.portfolio.models import HoldingCreate, HoldingUpdate, HoldingResponse
from src.core.portfolio.repository import HoldingRepository
from src.db.models import User

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/", response_model=List[HoldingResponse])
def list_holdings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all holdings for the current user."""
    repo = HoldingRepository(db)
    return repo.get_all(user_id=user.id)


@router.post("/", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
def add_holding(
    payload: HoldingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add a new holding."""
    repo = HoldingRepository(db)

    # Check if symbol already exists
    existing = repo.get_by_symbol(payload.symbol, user_id=user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Holding for {payload.symbol} already exists",
        )

    holding = repo.create(
        symbol=payload.symbol,
        shares=payload.shares,
        cost_basis=payload.cost_basis,
        purchase_date=payload.purchase_date,
        user_id=user.id,
    )
    return holding


@router.get("/{symbol}", response_model=HoldingResponse)
def get_holding(
    symbol: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific holding by symbol."""
    repo = HoldingRepository(db)
    holding = repo.get_by_symbol(symbol.upper(), user_id=user.id)
    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holding for {symbol.upper()} not found",
        )
    return holding


@router.patch("/{symbol}", response_model=HoldingResponse)
def update_holding(
    symbol: str,
    payload: HoldingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a holding."""
    repo = HoldingRepository(db)
    holding = repo.get_by_symbol(symbol.upper(), user_id=user.id)
    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holding for {symbol.upper()} not found",
        )

    updated = repo.update(
        holding_id=holding.id,
        shares=payload.shares,
        cost_basis=payload.cost_basis,
        purchase_date=payload.purchase_date,
    )
    return updated


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holding(
    symbol: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a holding by symbol."""
    repo = HoldingRepository(db)
    deleted = repo.delete_by_symbol(symbol.upper(), user_id=user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holding for {symbol.upper()} not found",
        )
