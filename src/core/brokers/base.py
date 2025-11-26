"""Base broker provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.brokers.models import BrokerAccount, BrokerPosition, LinkResult, BrokerType


class BrokerProvider(ABC):
    """Abstract base class for broker integrations.

    Each broker provider implements methods to:
    1. Create a link token for OAuth flow
    2. Exchange public token for access token
    3. Fetch accounts and positions
    4. Handle token refresh if needed
    """

    @property
    @abstractmethod
    def broker_type(self) -> BrokerType:
        """Return the broker type identifier."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Return human-readable broker name."""
        pass

    @abstractmethod
    def create_link_token(self, user_id: str) -> str:
        """Create a link token for the OAuth flow.

        Args:
            user_id: Internal user ID for tracking

        Returns:
            Link token to be used by frontend
        """
        pass

    @abstractmethod
    def exchange_public_token(self, public_token: str) -> LinkResult:
        """Exchange a public token for an access token.

        Called after user completes OAuth flow.

        Args:
            public_token: Token from OAuth callback

        Returns:
            LinkResult with access token and accounts
        """
        pass

    @abstractmethod
    def get_accounts(self, access_token: str) -> List[BrokerAccount]:
        """Fetch accounts for a linked connection.

        Args:
            access_token: Stored access token

        Returns:
            List of accounts with their positions
        """
        pass

    @abstractmethod
    def get_positions(
        self,
        access_token: str,
        account_id: Optional[str] = None,
    ) -> List[BrokerPosition]:
        """Fetch positions for an account.

        Args:
            access_token: Stored access token
            account_id: Optional account ID to filter by

        Returns:
            List of positions
        """
        pass

    @abstractmethod
    def refresh_token(self, access_token: str) -> Optional[str]:
        """Refresh an access token if needed.

        Args:
            access_token: Current access token

        Returns:
            New access token or None if refresh not needed/supported
        """
        pass

    @abstractmethod
    def is_token_valid(self, access_token: str) -> bool:
        """Check if an access token is still valid.

        Args:
            access_token: Access token to check

        Returns:
            True if token is valid
        """
        pass
