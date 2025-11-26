"""Broker position sync service."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from src.core.brokers.base import BrokerProvider
from src.core.brokers.models import BrokerPosition, BrokerType, SyncResult
from src.core.brokers.plaid_provider import plaid_provider
from src.core.portfolio.repository import HoldingRepository
from src.db.models import LinkedBrokerAccount, User

logger = logging.getLogger(__name__)


class BrokerSyncService:
    """Service for syncing positions from linked broker accounts."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = HoldingRepository(db)

    def get_provider(self, broker_type: str) -> Optional[BrokerProvider]:
        """Get the provider for a broker type."""
        if broker_type == BrokerType.PLAID.value:
            return plaid_provider
        # Add other providers here as needed
        return None

    def link_account(
        self,
        user: User,
        broker_type: str,
        public_token: str,
    ) -> LinkedBrokerAccount:
        """Link a new broker account after OAuth flow.

        Args:
            user: User to link account for
            broker_type: Type of broker (e.g., 'plaid')
            public_token: Public token from OAuth callback

        Returns:
            Created LinkedBrokerAccount
        """
        provider = self.get_provider(broker_type)
        if not provider:
            raise ValueError(f"Unsupported broker type: {broker_type}")

        # Exchange token and get accounts
        result = provider.exchange_public_token(public_token)

        if not result.success:
            raise RuntimeError(f"Failed to link account: {result.error_message}")

        # Create linked account for each broker account
        linked_accounts = []
        for account in result.accounts:
            linked = LinkedBrokerAccount(
                user_id=user.id,
                broker_type=broker_type,
                broker_name=f"{account.institution_name} - {account.account_name}",
                account_id=account.account_id,
                account_mask=account.account_mask,
                plaid_item_id=result.item_id,
                plaid_access_token=result.access_token,  # TODO: encrypt this
                sync_enabled=True,
                is_active=True,
            )
            self.db.add(linked)
            linked_accounts.append(linked)

        self.db.flush()

        # Return first account (or could return all)
        return linked_accounts[0] if linked_accounts else None

    def get_linked_accounts(self, user: User) -> List[LinkedBrokerAccount]:
        """Get all linked broker accounts for a user."""
        return (
            self.db.query(LinkedBrokerAccount)
            .filter(
                LinkedBrokerAccount.user_id == user.id,
                LinkedBrokerAccount.is_active == True,  # noqa: E712
            )
            .all()
        )

    def sync_account(
        self,
        account: LinkedBrokerAccount,
        force: bool = False,
    ) -> SyncResult:
        """Sync positions from a linked broker account.

        Args:
            account: Linked broker account to sync
            force: Force sync even if recently synced

        Returns:
            SyncResult with counts and errors
        """
        provider = self.get_provider(account.broker_type)
        if not provider:
            return SyncResult(
                success=False,
                positions_fetched=0,
                positions_synced=0,
                created=0,
                updated=0,
                skipped=0,
                errors=[f"Unsupported broker type: {account.broker_type}"],
                synced_at=datetime.utcnow(),
            )

        if not account.sync_enabled:
            return SyncResult(
                success=False,
                positions_fetched=0,
                positions_synced=0,
                created=0,
                updated=0,
                skipped=0,
                errors=["Sync disabled for this account"],
                synced_at=datetime.utcnow(),
            )

        try:
            # Fetch positions from broker
            positions = provider.get_positions(
                account.plaid_access_token,
                account_id=account.account_id,
            )

            # Sync to database
            result = self._sync_positions(
                user_id=account.user_id,
                positions=positions,
                mode=account.sync_mode,
            )

            # Update account sync status
            account.last_synced_at = datetime.utcnow()
            account.last_sync_error = None
            account.needs_reauth = False
            self.db.flush()

            return result

        except Exception as e:
            logger.error(f"Sync failed for account {account.id}: {e}")

            # Update error status
            account.last_sync_error = str(e)
            self.db.flush()

            return SyncResult(
                success=False,
                positions_fetched=0,
                positions_synced=0,
                created=0,
                updated=0,
                skipped=0,
                errors=[str(e)],
                synced_at=datetime.utcnow(),
            )

    def _sync_positions(
        self,
        user_id: str,
        positions: List[BrokerPosition],
        mode: str = "upsert",
    ) -> SyncResult:
        """Sync broker positions to holdings database.

        Args:
            user_id: User ID to sync for
            positions: Positions from broker
            mode: Sync mode ('upsert' or 'replace')

        Returns:
            SyncResult
        """
        created = 0
        updated = 0
        skipped = 0
        errors = []

        if mode == "replace":
            # Delete all existing holdings first
            existing = self.repo.get_all(user_id=user_id)
            for holding in existing:
                self.repo.delete(holding.id)

        for pos in positions:
            try:
                # Skip non-equity positions for now
                if pos.security_type not in ("equity", "etf", "mutual fund"):
                    skipped += 1
                    continue

                existing = self.repo.get_by_symbol(pos.symbol, user_id=user_id)

                if existing:
                    if mode == "upsert":
                        # Update existing
                        self.repo.update(
                            holding_id=existing.id,
                            shares=pos.shares,
                            cost_basis=pos.cost_basis_per_share or existing.cost_basis,
                        )
                        updated += 1
                    else:
                        skipped += 1
                else:
                    # Create new - skip if no cost basis (would break percentage rules)
                    if not pos.cost_basis_per_share or pos.cost_basis_per_share <= 0:
                        logger.warning(
                            f"Skipping {pos.symbol}: no valid cost basis "
                            f"(got {pos.cost_basis_per_share})"
                        )
                        skipped += 1
                        continue

                    self.repo.create(
                        symbol=pos.symbol,
                        shares=pos.shares,
                        cost_basis=pos.cost_basis_per_share,
                        user_id=user_id,
                    )
                    created += 1

            except Exception as e:
                errors.append(f"{pos.symbol}: {str(e)}")

        return SyncResult(
            success=len(errors) == 0,
            positions_fetched=len(positions),
            positions_synced=created + updated,
            created=created,
            updated=updated,
            skipped=skipped,
            errors=errors,
            synced_at=datetime.utcnow(),
        )

    def sync_all_accounts(self, user: User) -> List[SyncResult]:
        """Sync all linked accounts for a user.

        Returns:
            List of SyncResults, one per account
        """
        accounts = self.get_linked_accounts(user)
        results = []

        for account in accounts:
            result = self.sync_account(account)
            results.append(result)

        return results

    def unlink_account(self, account: LinkedBrokerAccount) -> bool:
        """Unlink (deactivate) a broker account.

        Doesn't delete the record, just marks inactive.
        """
        account.is_active = False
        account.sync_enabled = False
        self.db.flush()
        return True

    def delete_account(self, account: LinkedBrokerAccount) -> bool:
        """Permanently delete a linked broker account."""
        self.db.delete(account)
        self.db.flush()
        return True

    def check_account_status(self, account: LinkedBrokerAccount) -> bool:
        """Check if account connection is still valid.

        Returns True if valid, False if needs reauth.
        """
        provider = self.get_provider(account.broker_type)
        if not provider:
            return False

        is_valid = provider.is_token_valid(account.plaid_access_token)

        if not is_valid:
            account.needs_reauth = True

        return is_valid


def get_broker_sync_service(db: Session) -> BrokerSyncService:
    """Factory function for broker sync service."""
    return BrokerSyncService(db)
