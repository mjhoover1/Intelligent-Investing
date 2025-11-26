"""Portfolio position importers from various sources."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from io import StringIO
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.core.portfolio.repository import HoldingRepository
from src.db.models import Holding


@dataclass
class ImportedPosition:
    """A position parsed from an import source."""

    symbol: str
    shares: float
    cost_basis_per_share: float
    total_cost: float
    description: Optional[str] = None


@dataclass
class ImportResult:
    """Result of an import operation."""

    created: int
    updated: int
    skipped: int
    errors: List[str]
    positions: List[ImportedPosition]


def parse_currency(value: str) -> Optional[float]:
    """Parse a currency string like '$1,234.56' to float.

    Returns None if value is 'N/A' or unparseable.
    """
    if not value or value.strip() in ("N/A", "--", ""):
        return None

    # Remove $ and commas
    cleaned = value.replace("$", "").replace(",", "").strip()

    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_quantity(value: str) -> Optional[float]:
    """Parse a quantity string like '1,501' to float.

    Returns None if unparseable.
    """
    if not value or value.strip() in ("N/A", "--", ""):
        return None

    # Remove commas
    cleaned = value.replace(",", "").strip()

    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_schwab_csv(csv_content: str) -> Tuple[List[ImportedPosition], List[str]]:
    """Parse a Schwab positions CSV export.

    Schwab CSV format:
    - Line 1: Account header (e.g., "Positions for account...")
    - Line 2: Empty
    - Line 3: Column headers
    - Lines 4+: Data rows

    Args:
        csv_content: Raw CSV content as string

    Returns:
        Tuple of (positions list, error messages list)
    """
    positions: List[ImportedPosition] = []
    errors: List[str] = []

    # Split into lines and find the header row
    lines = csv_content.strip().split("\n")

    if len(lines) < 4:
        errors.append("CSV file too short - expected at least 4 lines")
        return positions, errors

    # Find the header row (contains "Symbol")
    header_idx = None
    for i, line in enumerate(lines):
        if '"Symbol"' in line or "Symbol" in line:
            header_idx = i
            break

    if header_idx is None:
        errors.append("Could not find header row with 'Symbol' column")
        return positions, errors

    # Parse from header row onwards
    csv_data = "\n".join(lines[header_idx:])
    reader = csv.DictReader(StringIO(csv_data))

    # Find the actual column names (Schwab uses long names)
    fieldnames = reader.fieldnames or []

    # Map to simplified names
    symbol_col = "Symbol"
    qty_col = None
    cost_col = None
    type_col = None

    for col in fieldnames:
        if "Qty" in col or "Quantity" in col:
            qty_col = col
        elif col == "Cost Basis":
            cost_col = col
        elif "Security Type" in col:
            type_col = col

    if not qty_col:
        errors.append("Could not find Quantity column")
        return positions, errors

    # Track positions by symbol for aggregation
    aggregated: Dict[str, ImportedPosition] = {}

    for row_num, row in enumerate(reader, start=header_idx + 2):
        try:
            symbol = row.get(symbol_col, "").strip()

            # Skip invalid rows
            if not symbol:
                continue

            # Skip special rows
            if symbol.lower() in ("cash & cash investments", "account total"):
                continue

            # Skip escrow/pending entries
            if symbol.upper() == "NO NUMBER":
                continue

            # Skip non-equity (though we might want warrants)
            security_type = row.get(type_col, "").strip() if type_col else ""
            if security_type and security_type.lower() not in ("equity", ""):
                if "warrant" not in security_type.lower():
                    continue

            # Parse quantity
            qty_str = row.get(qty_col, "")
            qty = parse_quantity(qty_str)

            if qty is None or qty <= 0:
                continue  # Skip zero or invalid positions

            # Parse cost basis (total, not per share)
            cost_str = row.get(cost_col, "") if cost_col else ""
            total_cost = parse_currency(cost_str)

            # Calculate per-share cost
            if total_cost is not None and qty > 0:
                cost_per_share = total_cost / qty
            else:
                # No cost basis - use 0 (user can update later)
                total_cost = 0.0
                cost_per_share = 0.0

            # Get description
            desc = row.get("Description", "").strip()

            # Aggregate if symbol already exists (e.g., multiple AUROW lots)
            if symbol in aggregated:
                existing = aggregated[symbol]
                new_total_shares = existing.shares + qty
                new_total_cost = existing.total_cost + (total_cost or 0)
                new_cost_per_share = (
                    new_total_cost / new_total_shares if new_total_shares > 0 else 0
                )

                aggregated[symbol] = ImportedPosition(
                    symbol=symbol,
                    shares=new_total_shares,
                    cost_basis_per_share=new_cost_per_share,
                    total_cost=new_total_cost,
                    description=existing.description,
                )
            else:
                aggregated[symbol] = ImportedPosition(
                    symbol=symbol,
                    shares=qty,
                    cost_basis_per_share=cost_per_share,
                    total_cost=total_cost or 0,
                    description=desc if desc else None,
                )

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    positions = list(aggregated.values())
    return positions, errors


def import_positions(
    db: Session,
    user_id: str,
    positions: List[ImportedPosition],
    mode: str = "upsert",
) -> ImportResult:
    """Import positions to the database.

    Args:
        db: Database session
        user_id: User ID to import for
        positions: List of positions to import
        mode: Import mode:
            - 'upsert': Update existing, create new (default)
            - 'replace': Delete all existing, then create new
            - 'add_only': Only create new, skip existing

    Returns:
        ImportResult with counts and any errors
    """
    repo = HoldingRepository(db)
    result = ImportResult(
        created=0,
        updated=0,
        skipped=0,
        errors=[],
        positions=positions,
    )

    if mode == "replace":
        # Delete all existing holdings for this user
        existing = repo.get_all(user_id=user_id)
        for holding in existing:
            repo.delete(holding.id)

    for pos in positions:
        try:
            existing = repo.get_by_symbol(pos.symbol, user_id=user_id)

            if existing:
                if mode == "add_only":
                    result.skipped += 1
                    continue

                # Update existing
                repo.update(
                    holding_id=existing.id,
                    shares=pos.shares,
                    cost_basis=pos.cost_basis_per_share,
                )
                result.updated += 1
            else:
                # Create new
                repo.create(
                    symbol=pos.symbol,
                    shares=pos.shares,
                    cost_basis=pos.cost_basis_per_share,
                    user_id=user_id,
                )
                result.created += 1

        except Exception as e:
            result.errors.append(f"{pos.symbol}: {str(e)}")

    return result


def import_schwab_csv(
    db: Session,
    user_id: str,
    csv_content: str,
    mode: str = "upsert",
) -> ImportResult:
    """Parse and import a Schwab CSV file.

    Args:
        db: Database session
        user_id: User ID to import for
        csv_content: Raw CSV content
        mode: Import mode ('upsert', 'replace', 'add_only')

    Returns:
        ImportResult with counts and any errors
    """
    positions, parse_errors = parse_schwab_csv(csv_content)

    if parse_errors:
        return ImportResult(
            created=0,
            updated=0,
            skipped=0,
            errors=parse_errors,
            positions=[],
        )

    result = import_positions(db, user_id, positions, mode)
    return result
