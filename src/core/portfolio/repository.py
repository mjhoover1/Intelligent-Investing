"""Portfolio repository for CRUD operations."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from src.db.models import Holding, User
from src.config import get_settings

settings = get_settings()


class HoldingRepository:
    """Repository for Holding CRUD operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def _get_or_create_default_user(self) -> User:
        """Get or create the default user for MVP mode."""
        user = self.db.query(User).filter_by(email=settings.default_user_email).first()
        if not user:
            user = User(email=settings.default_user_email)
            self.db.add(user)
            self.db.flush()  # Get the ID without committing
        return user

    def get_all(self, user_id: Optional[str] = None) -> list[Holding]:
        """Get all holdings for a user.

        Args:
            user_id: User ID. If None, uses default user.

        Returns:
            List of holdings
        """
        if user_id is None:
            user = self._get_or_create_default_user()
            user_id = user.id
        return self.db.query(Holding).filter_by(user_id=user_id).all()

    def get_by_id(self, holding_id: str) -> Optional[Holding]:
        """Get a holding by ID."""
        return self.db.query(Holding).filter_by(id=holding_id).first()

    def get_by_symbol(self, symbol: str, user_id: Optional[str] = None) -> Optional[Holding]:
        """Get a holding by symbol.

        Args:
            symbol: Stock ticker symbol
            user_id: User ID. If None, uses default user.

        Returns:
            Holding or None
        """
        symbol = symbol.upper()
        if user_id is None:
            user = self._get_or_create_default_user()
            user_id = user.id
        return (
            self.db.query(Holding)
            .filter_by(user_id=user_id, symbol=symbol)
            .first()
        )

    def create(
        self,
        symbol: str,
        shares: float,
        cost_basis: float,
        purchase_date: Optional[date] = None,
        user_id: Optional[str] = None,
    ) -> Holding:
        """Create a new holding.

        Args:
            symbol: Stock ticker symbol
            shares: Number of shares
            cost_basis: Cost basis per share
            purchase_date: Optional purchase date
            user_id: User ID. If None, uses default user.

        Returns:
            Created holding
        """
        symbol = symbol.upper()
        if user_id is None:
            user = self._get_or_create_default_user()
            user_id = user.id

        holding = Holding(
            user_id=user_id,
            symbol=symbol,
            shares=shares,
            cost_basis=cost_basis,
            purchase_date=purchase_date,
        )
        self.db.add(holding)
        self.db.flush()
        return holding

    def update(
        self,
        holding_id: str,
        shares: Optional[float] = None,
        cost_basis: Optional[float] = None,
        purchase_date: Optional[date] = None,
    ) -> Optional[Holding]:
        """Update a holding.

        Args:
            holding_id: Holding ID
            shares: New shares amount
            cost_basis: New cost basis
            purchase_date: New purchase date

        Returns:
            Updated holding or None if not found

        Raises:
            ValueError: If shares or cost_basis is invalid
        """
        holding = self.get_by_id(holding_id)
        if not holding:
            return None

        # Validate inputs
        if shares is not None and shares <= 0:
            raise ValueError(f"Shares must be positive, got {shares}")
        if cost_basis is not None and cost_basis <= 0:
            raise ValueError(f"Cost basis must be positive, got {cost_basis}")

        if shares is not None:
            holding.shares = shares
        if cost_basis is not None:
            holding.cost_basis = cost_basis
        if purchase_date is not None:
            holding.purchase_date = purchase_date

        self.db.flush()
        return holding

    def delete(self, holding_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a holding.

        Args:
            holding_id: Holding ID
            user_id: Optional user ID for ownership verification

        Returns:
            True if deleted, False if not found or unauthorized
        """
        holding = self.get_by_id(holding_id)
        if not holding:
            return False

        # Verify ownership if user_id provided
        if user_id is not None and holding.user_id != user_id:
            return False

        self.db.delete(holding)
        self.db.flush()
        return True

    def delete_by_symbol(self, symbol: str, user_id: Optional[str] = None) -> bool:
        """Delete a holding by symbol.

        Args:
            symbol: Stock ticker symbol
            user_id: User ID. If None, uses default user.

        Returns:
            True if deleted, False if not found
        """
        holding = self.get_by_symbol(symbol, user_id)
        if not holding:
            return False

        self.db.delete(holding)
        self.db.flush()
        return True
