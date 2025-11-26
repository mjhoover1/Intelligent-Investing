"""Broker integration module for automatic position syncing.

Supports:
- Plaid (12,000+ financial institutions)
- Direct broker integrations (future)

Usage:
    from src.core.brokers import BrokerSyncService, plaid_provider

    # Check if Plaid is configured
    if plaid_provider.is_configured():
        # Create link token for frontend
        link_token = plaid_provider.create_link_token(user_id)

    # Sync positions from linked account
    sync_service = BrokerSyncService(db)
    result = sync_service.sync_account(linked_account)
"""

from src.core.brokers.models import (
    BrokerType,
    BrokerPosition,
    BrokerAccount,
    LinkResult,
    SyncResult,
)
from src.core.brokers.base import BrokerProvider
from src.core.brokers.plaid_provider import PlaidProvider, plaid_provider
from src.core.brokers.sync import BrokerSyncService, get_broker_sync_service

__all__ = [
    # Models
    "BrokerType",
    "BrokerPosition",
    "BrokerAccount",
    "LinkResult",
    "SyncResult",
    # Providers
    "BrokerProvider",
    "PlaidProvider",
    "plaid_provider",
    # Services
    "BrokerSyncService",
    "get_broker_sync_service",
]
