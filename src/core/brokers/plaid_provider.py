"""Plaid broker integration provider.

Plaid provides a unified API to connect to 12,000+ financial institutions.
This provider handles the OAuth flow and position fetching via Plaid's
Investments product.

Setup:
1. Create a Plaid account at https://dashboard.plaid.com/
2. Get your client_id and secret from the dashboard
3. Set PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV in your .env

Note: Plaid Investments product requires a paid plan.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.config import get_settings
from src.core.brokers.base import BrokerProvider
from src.core.brokers.models import (
    BrokerAccount,
    BrokerPosition,
    BrokerType,
    LinkResult,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class PlaidProvider(BrokerProvider):
    """Plaid broker integration.

    Uses Plaid's API to connect to various brokerages and fetch positions.
    """

    def __init__(self):
        """Initialize Plaid client."""
        self._client = None
        self._initialized = False

    def _get_client(self):
        """Lazy-load the Plaid client."""
        if self._client is not None:
            return self._client

        # Check if Plaid is configured
        if not settings.plaid_client_id or not settings.plaid_secret:
            logger.warning("Plaid not configured - set PLAID_CLIENT_ID and PLAID_SECRET")
            return None

        try:
            import plaid
            from plaid.api import plaid_api
            from plaid.model.products import Products
            from plaid.model.country_code import CountryCode

            # Determine environment
            env = settings.plaid_env.lower()
            if env == "production":
                host = plaid.Environment.Production
            elif env == "development":
                host = plaid.Environment.Development
            else:
                host = plaid.Environment.Sandbox

            configuration = plaid.Configuration(
                host=host,
                api_key={
                    "clientId": settings.plaid_client_id,
                    "secret": settings.plaid_secret,
                },
            )

            api_client = plaid.ApiClient(configuration)
            self._client = plaid_api.PlaidApi(api_client)
            self._initialized = True
            logger.info(f"Plaid client initialized (env={env})")

        except ImportError:
            logger.warning("plaid-python not installed - run: pip install plaid-python")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Plaid client: {e}")
            return None

        return self._client

    @property
    def broker_type(self) -> BrokerType:
        return BrokerType.PLAID

    @property
    def display_name(self) -> str:
        return "Plaid"

    def is_configured(self) -> bool:
        """Check if Plaid is properly configured."""
        return bool(settings.plaid_client_id and settings.plaid_secret)

    def create_link_token(self, user_id: str) -> str:
        """Create a Plaid Link token for the frontend.

        The frontend uses this token to open Plaid Link, where users
        select their broker and authenticate.
        """
        client = self._get_client()
        if not client:
            raise RuntimeError("Plaid not configured")

        try:
            from plaid.model.link_token_create_request import LinkTokenCreateRequest
            from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
            from plaid.model.products import Products
            from plaid.model.country_code import CountryCode

            request = LinkTokenCreateRequest(
                products=[Products("investments")],
                client_name="Intelligent Investing",
                country_codes=[CountryCode("US")],
                language="en",
                user=LinkTokenCreateRequestUser(client_user_id=user_id),
            )

            response = client.link_token_create(request)
            return response["link_token"]

        except Exception as e:
            logger.error(f"Failed to create link token: {e}")
            raise

    def exchange_public_token(self, public_token: str) -> LinkResult:
        """Exchange public token from Plaid Link for access token."""
        client = self._get_client()
        if not client:
            return LinkResult(
                success=False,
                accounts=[],
                error_message="Plaid not configured",
            )

        try:
            from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

            # Exchange public token for access token
            exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
            exchange_response = client.item_public_token_exchange(exchange_request)

            access_token = exchange_response["access_token"]
            item_id = exchange_response["item_id"]

            # Fetch accounts
            accounts = self.get_accounts(access_token)

            return LinkResult(
                success=True,
                accounts=accounts,
                access_token=access_token,
                item_id=item_id,
            )

        except Exception as e:
            logger.error(f"Failed to exchange public token: {e}")
            return LinkResult(
                success=False,
                accounts=[],
                error_message=str(e),
            )

    def get_accounts(self, access_token: str) -> List[BrokerAccount]:
        """Fetch investment accounts from Plaid."""
        client = self._get_client()
        if not client:
            return []

        try:
            from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest

            request = InvestmentsHoldingsGetRequest(access_token=access_token)
            response = client.investments_holdings_get(request)

            # Build account list with positions
            accounts_map = {}
            securities_map = {s["security_id"]: s for s in response["securities"]}

            # First, create account entries
            for account in response["accounts"]:
                accounts_map[account["account_id"]] = BrokerAccount(
                    account_id=account["account_id"],
                    account_name=account["name"],
                    account_type=account.get("subtype", account.get("type", "brokerage")),
                    account_mask=account.get("mask"),
                    institution_name=response.get("item", {}).get("institution_id", "Unknown"),
                    positions=[],
                )

            # Add positions to accounts
            for holding in response["holdings"]:
                security = securities_map.get(holding["security_id"], {})
                symbol = security.get("ticker_symbol")

                if not symbol:
                    continue  # Skip holdings without ticker

                position = BrokerPosition(
                    symbol=symbol,
                    shares=holding["quantity"],
                    cost_basis_per_share=holding.get("cost_basis"),
                    current_price=security.get("close_price"),
                    account_id=holding["account_id"],
                    security_type=security.get("type", "equity"),
                    security_name=security.get("name"),
                )

                if holding["account_id"] in accounts_map:
                    accounts_map[holding["account_id"]].positions.append(position)

            return list(accounts_map.values())

        except Exception as e:
            logger.error(f"Failed to fetch accounts: {e}")
            return []

    def get_positions(
        self,
        access_token: str,
        account_id: Optional[str] = None,
    ) -> List[BrokerPosition]:
        """Fetch positions, optionally filtered by account."""
        accounts = self.get_accounts(access_token)
        positions = []

        for account in accounts:
            if account_id and account.account_id != account_id:
                continue
            positions.extend(account.positions)

        return positions

    def refresh_token(self, access_token: str) -> Optional[str]:
        """Plaid access tokens don't expire, but items may need reauth."""
        # Plaid tokens don't need refresh, but check item status
        return None

    def is_token_valid(self, access_token: str) -> bool:
        """Check if the Plaid item is still valid."""
        client = self._get_client()
        if not client:
            return False

        try:
            from plaid.model.item_get_request import ItemGetRequest

            request = ItemGetRequest(access_token=access_token)
            response = client.item_get(request)

            # Check for error status
            error = response.get("item", {}).get("error")
            if error:
                logger.warning(f"Plaid item has error: {error}")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to check token validity: {e}")
            return False


# Singleton instance
plaid_provider = PlaidProvider()
