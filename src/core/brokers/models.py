"""Broker integration data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


class BrokerType(str, Enum):
    """Supported broker types."""

    PLAID = "plaid"
    SCHWAB = "schwab"
    ROBINHOOD = "robinhood"
    FIDELITY = "fidelity"
    TD_AMERITRADE = "td_ameritrade"
    ETRADE = "etrade"
    INTERACTIVE_BROKERS = "interactive_brokers"


@dataclass
class BrokerPosition:
    """A position fetched from a broker."""

    symbol: str
    shares: float
    cost_basis_per_share: Optional[float]
    current_price: Optional[float]
    account_id: str
    security_type: str = "equity"  # equity, option, mutual_fund, etc.
    security_name: Optional[str] = None


@dataclass
class BrokerAccount:
    """An account from a broker."""

    account_id: str
    account_name: str
    account_type: str  # brokerage, ira, 401k, etc.
    account_mask: Optional[str]  # Last 4 digits
    institution_name: str
    positions: List[BrokerPosition]


@dataclass
class LinkResult:
    """Result of linking a broker account."""

    success: bool
    accounts: List[BrokerAccount]
    access_token: Optional[str] = None
    item_id: Optional[str] = None  # Plaid Item ID
    error_message: Optional[str] = None


@dataclass
class SyncResult:
    """Result of syncing positions from a broker."""

    success: bool
    positions_fetched: int
    positions_synced: int
    created: int
    updated: int
    skipped: int
    errors: List[str]
    synced_at: datetime
