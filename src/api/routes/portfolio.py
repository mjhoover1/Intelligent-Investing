"""Portfolio API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_current_user, require_api_key
from src.core.portfolio.models import HoldingCreate, HoldingUpdate, HoldingResponse
from src.core.portfolio.repository import HoldingRepository
from src.core.portfolio.importers import import_schwab_csv, parse_schwab_csv, ImportedPosition
from src.db.models import User

router = APIRouter(dependencies=[Depends(require_api_key)])


class ImportPositionPreview(BaseModel):
    """Preview of a position to be imported."""

    symbol: str
    shares: float
    cost_basis_per_share: float
    total_cost: float
    description: Optional[str]


class ImportPreviewResponse(BaseModel):
    """Response for import preview."""

    positions: List[ImportPositionPreview]
    total_positions: int
    errors: List[str]


class ImportResultResponse(BaseModel):
    """Response for import operation."""

    status: str
    created: int
    updated: int
    skipped: int
    errors: List[str]


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


@router.post("/import/schwab/preview", response_model=ImportPreviewResponse)
async def preview_schwab_import(
    file: UploadFile = File(..., description="Schwab positions CSV file"),
):
    """Preview what positions would be imported from a Schwab CSV.

    Upload a Schwab positions CSV to see what would be imported
    without making any changes.
    """
    # Read file content
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}",
        )

    # Parse CSV
    positions, errors = parse_schwab_csv(csv_content)

    return ImportPreviewResponse(
        positions=[
            ImportPositionPreview(
                symbol=p.symbol,
                shares=p.shares,
                cost_basis_per_share=p.cost_basis_per_share,
                total_cost=p.total_cost,
                description=p.description,
            )
            for p in positions
        ],
        total_positions=len(positions),
        errors=errors,
    )


@router.post("/import/schwab", response_model=ImportResultResponse)
async def import_schwab_positions(
    file: UploadFile = File(..., description="Schwab positions CSV file"),
    mode: str = Query(
        "upsert",
        description="Import mode: upsert (update existing), replace (delete all first), add_only (skip existing)",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Import positions from a Schwab CSV export.

    Modes:
    - upsert: Update existing positions, create new ones (default)
    - replace: Delete ALL existing positions first, then import
    - add_only: Only create new positions, skip any that already exist
    """
    # Validate mode
    if mode not in ("upsert", "replace", "add_only"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode: {mode}. Must be 'upsert', 'replace', or 'add_only'",
        )

    # Read file content
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}",
        )

    # Import
    result = import_schwab_csv(db, user.id, csv_content, mode)

    if result.errors and not result.positions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Import failed: {'; '.join(result.errors)}",
        )

    return ImportResultResponse(
        status="ok",
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        errors=result.errors,
    )
