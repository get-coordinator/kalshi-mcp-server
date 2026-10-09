"""Shared data models used across the server."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PriceRange:
    start: str
    end: str
    step: str


@dataclass
class MveSelectedLeg:
    event_ticker: str
    market_ticker: str
    side: str
    yes_settlement_value_dollars: str | None = None


@dataclass
class Market:
    # Required identifiers / core fields
    ticker: str
    event_ticker: str
    market_type: str
    title: str
    status: str

    # Optional strings
    subtitle: str | None = None
    series_ticker: str | None = None
    yes_sub_title: str | None = None
    no_sub_title: str | None = None
    created_time: str | None = None
    updated_time: str | None = None
    open_time: str | None = None
    close_time: str | None = None
    expiration_time: str | None = None
    latest_expiration_time: str | None = None
    response_price_units: str | None = None

    # Optional ints / numeric fields (often null)
    settlement_timer_seconds: int | None = None
    yes_bid: int | None = None
    yes_ask: int | None = None
    no_bid: int | None = None
    no_ask: int | None = None
    last_price: int | None = None
    volume: int | None = None
    volume_24h: int | None = None
    open_interest: int | None = None
    notional_value: int | None = None
    previous_yes_bid: int | None = None
    previous_yes_ask: int | None = None
    previous_price: int | None = None
    liquidity: int | None = None
    tick_size: int | None = None
    settlement_value: int | None = None
    # Kalshi can return these as decimal values (e.g. 78999.99), so treat as floats.
    floor_strike: float | None = None
    cap_strike: float | None = None

    # Optional dollar-string representations (often null)
    yes_bid_dollars: str | None = None
    yes_ask_dollars: str | None = None
    no_bid_dollars: str | None = None
    no_ask_dollars: str | None = None
    last_price_dollars: str | None = None
    volume_fp: str | None = None
    volume_24h_fp: str | None = None
    open_interest_fp: str | None = None
    notional_value_dollars: str | None = None
    previous_yes_bid_dollars: str | None = None
    previous_yes_ask_dollars: str | None = None
    previous_price_dollars: str | None = None
    liquidity_dollars: str | None = None
    settlement_value_dollars: str | None = None

    # Misc optional fields
    result: str | None = None
    can_close_early: bool | None = None
    expiration_value: str | None = None
    rules_primary: str | None = None
    rules_secondary: str | None = None
    price_level_structure: str | None = None
    price_ranges: list[PriceRange] | None = None
    expected_expiration_time: str | None = None
    settlement_ts: str | None = None
    fee_waiver_expiration_time: str | None = None
    early_close_condition: str | None = None
    strike_type: str | None = None
    functional_strike: str | None = None

    # Arbitrary JSON object; typed as `object` to avoid `Any` in public models.
    custom_strike: dict[str, object] | None = None

    mve_collection_ticker: str | None = None
    mve_selected_legs: list[MveSelectedLeg] | None = None
    primary_participant_key: str | None = None
    is_provisional: bool | None = None


@dataclass
class MarketsList:
    markets: list[Market]
    cursor: str | None = None


@dataclass
class Order:
    id: str
    market_id: str
    side: str
    quantity: int
    price: Optional[int] = None


@dataclass
class PortfolioOrder:
    # Required string fields
    order_id: str
    user_id: str
    client_order_id: str
    ticker: str
    status: str
    side: str
    action: str
    type: str

    # Required int fields
    yes_price: int
    no_price: int
    fill_count: int
    remaining_count: int
    initial_count: int
    taker_fees: int
    maker_fees: int
    taker_fill_cost: int
    maker_fill_cost: int
    queue_position: int

    # Required string (dollar) fields
    yes_price_dollars: str
    no_price_dollars: str
    fill_count_fp: str
    remaining_count_fp: str
    initial_count_fp: str
    taker_fill_cost_dollars: str
    maker_fill_cost_dollars: str

    # Optional string fields
    taker_fees_dollars: str | None = None
    maker_fees_dollars: str | None = None
    expiration_time: str | None = None
    created_time: str | None = None
    last_update_time: str | None = None
    self_trade_prevention_type: str | None = None
    order_group_id: str | None = None

    # Optional bool field
    cancel_order_on_pause: bool | None = None

    # Optional int field
    subaccount_number: int | None = None


@dataclass
class PortfolioOrdersList:
    orders: list[PortfolioOrder]
    cursor: str | None = None


@dataclass
class TagsByCategories:
    tags_by_categories: dict[str, list[str]]


@dataclass
class PortfolioBalance:
    """Member balance and portfolio value (both in cents)."""

    balance: int
    portfolio_value: int
    updated_ts: int


@dataclass
class SubaccountBalance:
    subaccount_number: int
    balance: str
    updated_ts: int


@dataclass
class SubaccountBalancesList:
    subaccount_balances: list[SubaccountBalance]


@dataclass
class SettlementSource:
    name: str
    url: str


@dataclass
class Series:
    ticker: str
    frequency: str
    title: str
    category: str
    # Kalshi API sometimes returns `null` for tags/additional_prohibitions.
    tags: list[str] | None
    settlement_sources: list[SettlementSource]
    contract_url: str
    contract_terms_url: str
    fee_type: str
    fee_multiplier: float
    additional_prohibitions: list[str] | None
    product_metadata: dict[str, object] | None = None
    volume: int | None = None
    volume_fp: str | None = None


@dataclass
class SeriesList:
    series: list[Series]
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class MarketPosition:
    """A single market-level position from GET /portfolio/positions."""
    ticker: str
    total_traded: int
    total_traded_dollars: str
    position: int
    position_fp: str
    market_exposure: int
    market_exposure_dollars: str
    realized_pnl: int
    realized_pnl_dollars: str
    resting_orders_count: int
    fees_paid: int
    fees_paid_dollars: str
    last_updated_ts: str | None = None


@dataclass(frozen=True, slots=True)
class EventPosition:
    """A single event-level position from GET /portfolio/positions."""
    event_ticker: str
    total_cost: int
    total_cost_dollars: str
    total_cost_shares: int
    total_cost_shares_fp: str
    event_exposure: int
    event_exposure_dollars: str
    realized_pnl: int
    realized_pnl_dollars: str
    fees_paid: int
    fees_paid_dollars: str
    resting_orders_count: int | None = None


@dataclass(frozen=True, slots=True)
class PortfolioPositions:
    """Response from GET /portfolio/positions."""
    cursor: str | None
    market_positions: list[MarketPosition]
    event_positions: list[EventPosition]
