"""Broker integration API routes."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_current_user
from src.core.brokers import BrokerSyncService, plaid_provider, BrokerType
from src.db.models import LinkedBrokerAccount, User

router = APIRouter(prefix="/brokers", tags=["brokers"])


# Request/Response Models

class BrokerStatusResponse(BaseModel):
    """Broker integration status."""

    plaid_configured: bool
    plaid_env: Optional[str]


class LinkedAccountResponse(BaseModel):
    """Linked broker account response."""

    id: str
    broker_type: str
    broker_name: Optional[str]
    account_mask: Optional[str]
    sync_enabled: bool
    sync_mode: str
    last_synced_at: Optional[datetime]
    last_sync_error: Optional[str]
    needs_reauth: bool
    is_active: bool


class CreateLinkTokenResponse(BaseModel):
    """Response for creating a Plaid link token."""

    link_token: str


class ExchangeTokenRequest(BaseModel):
    """Request to exchange public token after OAuth."""

    public_token: str
    broker_type: str = "plaid"


class SyncResultResponse(BaseModel):
    """Response for sync operation."""

    success: bool
    positions_fetched: int
    positions_synced: int
    created: int
    updated: int
    skipped: int
    errors: List[str]


class UpdateSyncSettingsRequest(BaseModel):
    """Request to update sync settings."""

    sync_enabled: Optional[bool] = None
    sync_mode: Optional[str] = None


# Routes

@router.get("/status", response_model=BrokerStatusResponse)
def get_broker_status():
    """Get broker integration status."""
    from src.config import get_settings
    settings = get_settings()

    return BrokerStatusResponse(
        plaid_configured=plaid_provider.is_configured(),
        plaid_env=settings.plaid_env if plaid_provider.is_configured() else None,
    )


@router.get("/accounts", response_model=List[LinkedAccountResponse])
def list_linked_accounts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List linked broker accounts for current user."""
    sync_service = BrokerSyncService(db)
    accounts = sync_service.get_linked_accounts(user)

    return [
        LinkedAccountResponse(
            id=acc.id,
            broker_type=acc.broker_type,
            broker_name=acc.broker_name,
            account_mask=acc.account_mask,
            sync_enabled=acc.sync_enabled,
            sync_mode=acc.sync_mode,
            last_synced_at=acc.last_synced_at,
            last_sync_error=acc.last_sync_error,
            needs_reauth=acc.needs_reauth,
            is_active=acc.is_active,
        )
        for acc in accounts
    ]


@router.post("/link/plaid/token", response_model=CreateLinkTokenResponse)
def create_plaid_link_token(
    user: User = Depends(get_current_user),
):
    """Create a Plaid Link token to initiate account linking.

    The frontend uses this token to open Plaid Link.
    """
    if not plaid_provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plaid integration not configured",
        )

    try:
        link_token = plaid_provider.create_link_token(user.id)
        return CreateLinkTokenResponse(link_token=link_token)
    except Exception:
        # Log the actual error server-side but don't expose to client
        import logging
        logging.getLogger(__name__).exception("Failed to create Plaid link token")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create link token. Please try again later.",
        )


@router.post("/link/exchange", response_model=LinkedAccountResponse)
def exchange_public_token(
    request: ExchangeTokenRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Exchange public token from OAuth callback for access token.

    Called after user completes Plaid Link flow.
    """
    sync_service = BrokerSyncService(db)

    try:
        account = sync_service.link_account(
            user=user,
            broker_type=request.broker_type,
            public_token=request.public_token,
        )

        if not account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No accounts found in linked connection",
            )

        db.commit()

        return LinkedAccountResponse(
            id=account.id,
            broker_type=account.broker_type,
            broker_name=account.broker_name,
            account_mask=account.account_mask,
            sync_enabled=account.sync_enabled,
            sync_mode=account.sync_mode,
            last_synced_at=account.last_synced_at,
            last_sync_error=account.last_sync_error,
            needs_reauth=account.needs_reauth,
            is_active=account.is_active,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/accounts/{account_id}/sync", response_model=SyncResultResponse)
def sync_account(
    account_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sync positions from a linked broker account."""
    account = (
        db.query(LinkedBrokerAccount)
        .filter(
            LinkedBrokerAccount.id == account_id,
            LinkedBrokerAccount.user_id == user.id,
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    sync_service = BrokerSyncService(db)
    result = sync_service.sync_account(account)
    db.commit()

    return SyncResultResponse(
        success=result.success,
        positions_fetched=result.positions_fetched,
        positions_synced=result.positions_synced,
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        errors=result.errors,
    )


@router.post("/sync-all", response_model=List[SyncResultResponse])
def sync_all_accounts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sync positions from all linked broker accounts."""
    sync_service = BrokerSyncService(db)
    results = sync_service.sync_all_accounts(user)
    db.commit()

    return [
        SyncResultResponse(
            success=r.success,
            positions_fetched=r.positions_fetched,
            positions_synced=r.positions_synced,
            created=r.created,
            updated=r.updated,
            skipped=r.skipped,
            errors=r.errors,
        )
        for r in results
    ]


@router.patch("/accounts/{account_id}", response_model=LinkedAccountResponse)
def update_account_settings(
    account_id: str,
    request: UpdateSyncSettingsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update sync settings for a linked account."""
    account = (
        db.query(LinkedBrokerAccount)
        .filter(
            LinkedBrokerAccount.id == account_id,
            LinkedBrokerAccount.user_id == user.id,
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    if request.sync_enabled is not None:
        account.sync_enabled = request.sync_enabled

    if request.sync_mode is not None:
        if request.sync_mode not in ("upsert", "replace"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid sync mode. Must be 'upsert' or 'replace'",
            )
        account.sync_mode = request.sync_mode

    db.commit()

    return LinkedAccountResponse(
        id=account.id,
        broker_type=account.broker_type,
        broker_name=account.broker_name,
        account_mask=account.account_mask,
        sync_enabled=account.sync_enabled,
        sync_mode=account.sync_mode,
        last_synced_at=account.last_synced_at,
        last_sync_error=account.last_sync_error,
        needs_reauth=account.needs_reauth,
        is_active=account.is_active,
    )


@router.delete("/accounts/{account_id}")
def unlink_account(
    account_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Unlink (deactivate) a broker account."""
    account = (
        db.query(LinkedBrokerAccount)
        .filter(
            LinkedBrokerAccount.id == account_id,
            LinkedBrokerAccount.user_id == user.id,
        )
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    sync_service = BrokerSyncService(db)
    sync_service.unlink_account(account)
    db.commit()

    return {"status": "ok", "message": "Account unlinked"}
