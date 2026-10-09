"""MCP tool handlers."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from typing import Any, Callable

from ..models import (
    EventPosition,
    Market,
    MarketPosition,
    MarketsList,
    MveSelectedLeg,
    PortfolioBalance,
    PortfolioOrder,
    PortfolioOrdersList,
    PortfolioPositions,
    PriceRange,
    Series,
    SeriesList,
    SettlementSource,
    SubaccountBalance,
    SubaccountBalancesList,
    TagsByCategories,
)
from ..services import MetadataService, PortfolioService

ToolHandler = Callable[[dict[str, Any] | None], dict[str, Any]]


def _require_arguments(arguments: dict[str, Any] | None, tool_name: str) -> dict[str, Any]:
    if arguments is None:
        raise ValueError(f"Missing arguments for {tool_name}.")
    return arguments


def _parse_required_str(
    arguments: dict[str, Any],
    key: str,
    *,
    type_error: str,
    empty_error: str | None = None,
) -> str:
    value = arguments.get(key)
    if not isinstance(value, str):
        raise ValueError(type_error)
    normalized = value.strip()
    if empty_error is not None and not normalized:
        raise ValueError(empty_error)
    return normalized


def _parse_optional_str(
    arguments: dict[str, Any],
    key: str,
    *,
    type_error: str,
    empty_error: str,
) -> str | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(type_error)
    normalized = value.strip()
    if not normalized:
        raise ValueError(empty_error)
    return normalized


def _parse_optional_int(
    arguments: dict[str, Any],
    key: str,
    *,
    type_error: str,
    range_error: str,
    min_value: int,
    max_value: int,
) -> int | None:
    value = arguments.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(type_error)
    if value < min_value or value > max_value:
        raise ValueError(range_error)
    return value


def _parse_bool(arguments: dict[str, Any], key: str, default: bool, *, type_error: str) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(type_error)
    return value


def _parse_positions_count_filter(value: str) -> str:
    allowed_fields = {"position", "total_traded"}
    parts = [item.strip() for item in value.split(",")]
    if any(not item for item in parts):
        raise ValueError(
            "count_filter must be a comma-separated list containing only position and/or total_traded."
        )

    unknown = [item for item in parts if item not in allowed_fields]
    if unknown:
        raise ValueError(
            "count_filter must be a comma-separated list containing only position and/or total_traded."
        )

    # Preserve caller order while dropping duplicates.
    unique_parts = list(dict.fromkeys(parts))
    return ",".join(unique_parts)


def build_tool_handlers(
    metadata_service: MetadataService, portfolio_service: PortfolioService
) -> dict[str, ToolHandler]:
    return {
        "get_tags_for_series_categories": lambda arguments: (
            handle_get_tags_for_series_categories(metadata_service, arguments)
        ),
        "get_balance": lambda arguments: (
            handle_get_balance(portfolio_service, arguments)
        ),
        "get_subaccount_balances": lambda arguments: (
            handle_get_subaccount_balances(portfolio_service, arguments)
        ),
        "get_categories": lambda arguments: (
            handle_get_categories(metadata_service, arguments)
        ),
        "get_tags_for_series_category": lambda arguments: (
            handle_get_tags_for_series_category(metadata_service, arguments)
        ),
        "get_series_list": lambda arguments: (
            handle_get_series_list(metadata_service, arguments)
        ),
        "get_markets": lambda arguments: (
            handle_get_markets(metadata_service, arguments)
        ),
        "get_open_markets_for_series": lambda arguments: (
            handle_get_open_markets_for_series(metadata_service, arguments)
        ),
        "get_open_market_titles_for_series": lambda arguments: (
            handle_get_open_market_titles_for_series(metadata_service, arguments)
        ),
        "get_series_tickers_for_category": lambda arguments: (
            handle_get_series_tickers_for_category(metadata_service, arguments)
        ),
        "search_markets": lambda arguments: (
            handle_search_markets(metadata_service, arguments)
        ),
        "get_orders": lambda arguments: (
            handle_get_orders(portfolio_service, arguments)
        ),
        "get_order": lambda arguments: (
            handle_get_order(portfolio_service, arguments)
        ),
        "get_positions": lambda arguments: (
            handle_get_positions(portfolio_service, arguments)
        ),
    }


def handle_get_tags_for_series_categories(
    metadata_service: MetadataService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    if arguments:
        raise ValueError("get_tags_for_series_categories does not accept arguments.")

    tags = metadata_service.get_tags_for_series_categories()
    return _serialize_tags(tags)


def _serialize_tags(tags: TagsByCategories) -> dict[str, Any]:
    return {"tags_by_categories": tags.tags_by_categories}


def handle_get_balance(
    portfolio_service: PortfolioService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    if arguments:
        raise ValueError("get_balance does not accept arguments.")

    balance = portfolio_service.get_balance()
    return _serialize_balance(balance)


def _serialize_balance(balance: PortfolioBalance) -> dict[str, Any]:
    return {
        "balance": balance.balance,
        "portfolio_value": balance.portfolio_value,
        "updated_ts": balance.updated_ts,
    }


def handle_get_subaccount_balances(
    portfolio_service: PortfolioService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    if arguments:
        raise ValueError("get_subaccount_balances does not accept arguments.")

    result = portfolio_service.get_subaccount_balances()
    return _serialize_subaccount_balances(result)


def _serialize_subaccount_balances(result: SubaccountBalancesList) -> dict[str, Any]:
    return {
        "subaccount_balances": [
            _serialize_subaccount_balance(item) for item in result.subaccount_balances
        ],
    }


def _serialize_subaccount_balance(item: SubaccountBalance) -> dict[str, Any]:
    return {
        "subaccount_number": item.subaccount_number,
        "balance": item.balance,
        "updated_ts": item.updated_ts,
    }


def handle_get_categories(
    metadata_service: MetadataService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    if arguments:
        raise ValueError("get_categories does not accept arguments.")

    categories = metadata_service.get_categories()
    return {"categories": categories}


def handle_get_tags_for_series_category(
    metadata_service: MetadataService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    args = _require_arguments(arguments, "get_tags_for_series_category")
    category = _parse_required_str(
        args,
        "category",
        type_error="category must be a string.",
        empty_error="category must be a non-empty string.",
    )

    tags = metadata_service.get_tags_for_series_category(category)
    return {"category": category, "tags": tags}


def handle_get_series_list(
    metadata_service: MetadataService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    category: str | None = None
    tags: str | None = None
    cursor: str | None = None
    limit: int | None = None
    include_product_metadata = False
    include_volume = False

    if arguments is not None:
        category = _parse_optional_str(
            arguments,
            "category",
            type_error="category must be a string.",
            empty_error="category must be a non-empty string.",
        )
        tags = _parse_optional_str(
            arguments,
            "tags",
            type_error="tags must be a string.",
            empty_error="tags must be a non-empty string.",
        )
        cursor = _parse_optional_str(
            arguments,
            "cursor",
            type_error="cursor must be a string.",
            empty_error="cursor must be a non-empty string.",
        )
        limit = _parse_optional_int(
            arguments,
            "limit",
            type_error="limit must be an integer.",
            range_error="limit must be between 1 and 1000.",
            min_value=1,
            max_value=1000,
        )
        include_product_metadata = _parse_bool(
            arguments,
            "include_product_metadata",
            False,
            type_error="include_product_metadata must be a boolean.",
        )
        include_volume = _parse_bool(
            arguments,
            "include_volume",
            False,
            type_error="include_volume must be a boolean.",
        )

    series_list = metadata_service.get_series_list(
        category=category,
        tags=tags,
        cursor=cursor,
        limit=limit,
        include_product_metadata=include_product_metadata,
        include_volume=include_volume,
    )
    return _serialize_series_list(series_list)


def handle_get_markets(
    metadata_service: MetadataService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    cursor: str | None = None
    limit: int | None = None
    event_ticker: str | None = None
    series_ticker: str | None = None
    tickers: str | None = None
    status: str | None = None
    mve_filter: str | None = None
    min_created_ts: int | None = None
    max_created_ts: int | None = None
    min_updated_ts: int | None = None
    min_close_ts: int | None = None
    max_close_ts: int | None = None
    min_settled_ts: int | None = None
    max_settled_ts: int | None = None

    if arguments is not None:
        cursor = _parse_optional_str(
            arguments,
            "cursor",
            type_error="cursor must be a string.",
            empty_error="cursor must be a non-empty string.",
        )
        limit = _parse_optional_int(
            arguments,
            "limit",
            type_error="limit must be an integer.",
            range_error="limit must be between 1 and 1000.",
            min_value=1,
            max_value=1000,
        )
        event_ticker = _parse_optional_str(
            arguments,
            "event_ticker",
            type_error="event_ticker must be a string.",
            empty_error="event_ticker must be a non-empty string.",
        )
        series_ticker = _parse_optional_str(
            arguments,
            "series_ticker",
            type_error="series_ticker must be a string.",
            empty_error="series_ticker must be a non-empty string.",
        )
        tickers = _parse_optional_str(
            arguments,
            "tickers",
            type_error="tickers must be a string.",
            empty_error="tickers must be a non-empty string.",
        )
        status = _parse_optional_str(
            arguments,
            "status",
            type_error="status must be a string.",
            empty_error="status must be a non-empty string.",
        )

        mve_filter = _parse_optional_str(
            arguments,
            "mve_filter",
            type_error="mve_filter must be a string.",
            empty_error="mve_filter must be a non-empty string.",
        )
        if mve_filter is not None:
            allowed_mve = {"only", "exclude"}
            if mve_filter not in allowed_mve:
                raise ValueError("mve_filter must be one of only, exclude.")

        ts_max = 10_000_000_000
        min_created_ts = _parse_optional_int(
            arguments,
            "min_created_ts",
            type_error="min_created_ts must be an integer.",
            range_error="min_created_ts must be a non-negative integer.",
            min_value=0,
            max_value=ts_max,
        )
        max_created_ts = _parse_optional_int(
            arguments,
            "max_created_ts",
            type_error="max_created_ts must be an integer.",
            range_error="max_created_ts must be a non-negative integer.",
            min_value=0,
            max_value=ts_max,
        )
        min_updated_ts = _parse_optional_int(
            arguments,
            "min_updated_ts",
            type_error="min_updated_ts must be an integer.",
            range_error="min_updated_ts must be a non-negative integer.",
            min_value=0,
            max_value=ts_max,
        )
        min_close_ts = _parse_optional_int(
            arguments,
            "min_close_ts",
            type_error="min_close_ts must be an integer.",
            range_error="min_close_ts must be a non-negative integer.",
            min_value=0,
            max_value=ts_max,
        )
        max_close_ts = _parse_optional_int(
            arguments,
            "max_close_ts",
            type_error="max_close_ts must be an integer.",
            range_error="max_close_ts must be a non-negative integer.",
            min_value=0,
            max_value=ts_max,
        )
        min_settled_ts = _parse_optional_int(
            arguments,
            "min_settled_ts",
            type_error="min_settled_ts must be an integer.",
            range_error="min_settled_ts must be a non-negative integer.",
            min_value=0,
            max_value=ts_max,
        )
        max_settled_ts = _parse_optional_int(
            arguments,
            "max_settled_ts",
            type_error="max_settled_ts must be an integer.",
            range_error="max_settled_ts must be a non-negative integer.",
            min_value=0,
            max_value=ts_max,
        )

    markets_list = metadata_service.get_markets(
        cursor=cursor,
        limit=limit,
        event_ticker=event_ticker,
        series_ticker=series_ticker,
        tickers=tickers,
        status=status,
        mve_filter=mve_filter,
        min_created_ts=min_created_ts,
        max_created_ts=max_created_ts,
        min_updated_ts=min_updated_ts,
        min_close_ts=min_close_ts,
        max_close_ts=max_close_ts,
        min_settled_ts=min_settled_ts,
        max_settled_ts=max_settled_ts,
    )
    return _serialize_markets_list(markets_list)


def _page_open_markets_for_series(
    metadata_service: MetadataService,
    *,
    series_ticker: str,
    limit: int,
    max_pages: int,
) -> tuple[list[Market], int]:
    markets: list[Market] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    pages = 0

    while True:
        if pages >= max_pages:
            raise ValueError(
                "Exceeded max_pages while paging /markets; reduce scope or increase max_pages."
            )

        markets_list = metadata_service.get_markets(
            cursor=cursor,
            limit=limit,
            series_ticker=series_ticker,
            status="open",
        )
        markets.extend(markets_list.markets)

        pages += 1
        next_cursor = markets_list.cursor
        if next_cursor is None:
            break

        # Protect against a buggy/looping cursor.
        if next_cursor in seen_cursors:
            raise ValueError("Kalshi /markets cursor repeated; aborting pagination.")
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    return markets, pages


def _page_series_tickers_for_category(
    metadata_service: MetadataService,
    *,
    category: str,
    tags: str | None,
    limit: int,
    max_pages: int,
) -> tuple[list[str], int]:
    tickers: list[str] = []
    seen_tickers: set[str] = set()
    cursor: str | None = None
    seen_cursors: set[str] = set()
    pages = 0

    while True:
        if pages >= max_pages:
            raise ValueError(
                "Exceeded max_pages while paging /series; "
                "reduce scope with tags or increase max_pages."
            )

        series_list = metadata_service.get_series_list(
            category=category,
            tags=tags,
            cursor=cursor,
            limit=limit,
            include_product_metadata=False,
            include_volume=False,
        )

        for series in series_list.series:
            if series.ticker not in seen_tickers:
                seen_tickers.add(series.ticker)
                tickers.append(series.ticker)

        pages += 1
        next_cursor = series_list.cursor
        if next_cursor is None:
            break

        # Protect against a buggy/looping cursor.
        if next_cursor in seen_cursors:
            raise ValueError("Kalshi /series cursor repeated; aborting pagination.")
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    return tickers, pages


def handle_get_open_markets_for_series(
    metadata_service: MetadataService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    args = _require_arguments(arguments, "get_open_markets_for_series")
    series_ticker = _parse_required_str(
        args,
        "series_ticker",
        type_error="series_ticker must be a string.",
        empty_error="series_ticker must be a non-empty string.",
    )

    # Default to max Kalshi page size to minimize API round-trips.
    limit = (
        _parse_optional_int(
            args,
            "limit",
            type_error="limit must be an integer.",
            range_error="limit must be between 1 and 1000.",
            min_value=1,
            max_value=1000,
        )
        or 1000
    )
    max_pages = (
        _parse_optional_int(
            args,
            "max_pages",
            type_error="max_pages must be an integer.",
            range_error="max_pages must be between 1 and 10000.",
            min_value=1,
            max_value=10000,
        )
        or 1000
    )

    days = (
        _parse_optional_int(
            args,
            "closes_within_days",
            type_error="closes_within_days must be an integer.",
            range_error="closes_within_days must be between 1 and 365.",
            min_value=1,
            max_value=365,
        )
        or 8
    )
    most = (
        _parse_optional_int(
            args,
            "max_markets",
            type_error="max_markets must be an integer.",
            range_error="max_markets must be between 1 and 500.",
            min_value=1,
            max_value=500,
        )
        or 60
    )

    markets, pages = _page_open_markets_for_series(
        metadata_service, series_ticker=series_ticker, limit=limit, max_pages=max_pages
    )
    cutoff = datetime.now(timezone.utc) + timedelta(days=days)
    soon = [m for m in markets if _closes_before(m.close_time, cutoff)]
    busiest = sorted(soon, key=lambda m: -_number(m.volume_24h_fp))[:most]
    return {
        "series_ticker": series_ticker,
        "status": "open",
        "closes_within_days": days,
        "markets": [_compact_market(m) for m in busiest],
        "count": len(busiest),
        "more_markets": len(soon) - len(busiest),
        "pages": pages,
    }


def _closes_before(close_time: str | None, cutoff: datetime) -> bool:
    if not close_time:
        return True
    try:
        return datetime.fromisoformat(close_time.replace("Z", "+00:00")) <= cutoff
    except ValueError:
        return True


def _number(value: str | None) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def handle_get_open_market_titles_for_series(
    metadata_service: MetadataService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    args = _require_arguments(arguments, "get_open_market_titles_for_series")
    series_ticker = _parse_required_str(
        args,
        "series_ticker",
        type_error="series_ticker must be a string.",
        empty_error="series_ticker must be a non-empty string.",
    )

    # Default to max Kalshi page size to minimize API round-trips.
    limit = (
        _parse_optional_int(
            args,
            "limit",
            type_error="limit must be an integer.",
            range_error="limit must be between 1 and 1000.",
            min_value=1,
            max_value=1000,
        )
        or 1000
    )
    max_pages = (
        _parse_optional_int(
            args,
            "max_pages",
            type_error="max_pages must be an integer.",
            range_error="max_pages must be between 1 and 10000.",
            min_value=1,
            max_value=10000,
        )
        or 1000
    )

    markets, pages = _page_open_markets_for_series(
        metadata_service, series_ticker=series_ticker, limit=limit, max_pages=max_pages
    )
    return {
        "series_ticker": series_ticker,
        "status": "open",
        "markets": [
            {
                "ticker": m.ticker,
                "title": m.title,
                "subtitle": m.subtitle,
                "yes_sub_title": m.yes_sub_title,
                "no_sub_title": m.no_sub_title,
            }
            for m in markets
        ],
        "count": len(markets),
        "pages": pages,
    }


def handle_get_series_tickers_for_category(
    metadata_service: MetadataService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    args = _require_arguments(arguments, "get_series_tickers_for_category")

    category = _parse_required_str(
        args,
        "category",
        type_error="category must be a string.",
        empty_error="category must be a non-empty string.",
    )
    tags = _parse_optional_str(
        args,
        "tags",
        type_error="tags must be a string.",
        empty_error="tags must be a non-empty string.",
    )

    # Default to max Kalshi page size to minimize API round-trips.
    limit = (
        _parse_optional_int(
            args,
            "limit",
            type_error="limit must be an integer.",
            range_error="limit must be between 1 and 1000.",
            min_value=1,
            max_value=1000,
        )
        or 1000
    )

    max_pages = (
        _parse_optional_int(
            args,
            "max_pages",
            type_error="max_pages must be an integer.",
            range_error="max_pages must be between 1 and 10000.",
            min_value=1,
            max_value=10000,
        )
        or 1000
    )

    tickers, pages = _page_series_tickers_for_category(
        metadata_service, category=category, tags=tags, limit=limit, max_pages=max_pages
    )

    payload: dict[str, Any] = {
        "category": category,
        "tickers": tickers,
        "count": len(tickers),
        "pages": pages,
    }
    if tags is not None:
        payload["tags"] = tags
    return payload


def _serialize_series_list(series_list: SeriesList) -> dict[str, Any]:
    serialized: dict[str, Any] = {"series": [_serialize_series(item) for item in series_list.series]}
    if series_list.cursor is not None:
        serialized["cursor"] = series_list.cursor
    return serialized


def _serialize_series(series: Series) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ticker": series.ticker,
        "frequency": series.frequency,
        "title": series.title,
        "category": series.category,
        "tags": series.tags,
        "settlement_sources": [
            _serialize_settlement_source(source) for source in series.settlement_sources
        ],
        "contract_url": series.contract_url,
        "contract_terms_url": series.contract_terms_url,
        "fee_type": series.fee_type,
        "fee_multiplier": series.fee_multiplier,
        "additional_prohibitions": series.additional_prohibitions,
    }
    if series.product_metadata is not None:
        payload["product_metadata"] = series.product_metadata
    if series.volume is not None:
        payload["volume"] = series.volume
    if series.volume_fp is not None:
        payload["volume_fp"] = series.volume_fp

    return payload


def _serialize_settlement_source(source: SettlementSource) -> dict[str, str]:
    return {"name": source.name, "url": source.url}


def _serialize_markets_list(markets_list: MarketsList) -> dict[str, Any]:
    serialized: dict[str, Any] = {"markets": [_compact_market(item) for item in markets_list.markets]}
    if markets_list.cursor is not None:
        serialized["cursor"] = markets_list.cursor
    return serialized


def _compact_market(market: Market) -> dict[str, Any]:
    """A market as a line: who, its prices and volume, when it closes. A slate of
    full market objects (rules text and all) overflows what the caller can read."""
    row: dict[str, Any] = {"ticker": market.ticker, "title": market.title}
    for key in ("yes_sub_title", "status", "yes_bid_dollars", "yes_ask_dollars", "last_price_dollars",
                "previous_price_dollars", "volume_fp", "volume_24h_fp", "close_time"):
        value = getattr(market, key, None)
        if value not in (None, ""):
            row[key] = value
    return row


def handle_get_order(
    portfolio_service: PortfolioService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    args = _require_arguments(arguments, "get_order")
    order_id = _parse_required_str(
        args,
        "order_id",
        type_error="order_id must be a string.",
        empty_error="order_id must be a non-empty string.",
    )
    order = portfolio_service.get_order(order_id)
    return _serialize_order(order)


def handle_get_orders(
    portfolio_service: PortfolioService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    ticker: str | None = None
    event_ticker: str | None = None
    min_ts: int | None = None
    max_ts: int | None = None
    status: str | None = None
    limit: int | None = None
    cursor: str | None = None
    subaccount: int | None = None

    if arguments is not None:
        ticker = _parse_optional_str(
            arguments,
            "ticker",
            type_error="ticker must be a string.",
            empty_error="ticker must be a non-empty string.",
        )
        event_ticker = _parse_optional_str(
            arguments,
            "event_ticker",
            type_error="event_ticker must be a string.",
            empty_error="event_ticker must be a non-empty string.",
        )
        cursor = _parse_optional_str(
            arguments,
            "cursor",
            type_error="cursor must be a string.",
            empty_error="cursor must be a non-empty string.",
        )

        status = _parse_optional_str(
            arguments,
            "status",
            type_error="status must be a string.",
            empty_error="status must be a non-empty string.",
        )
        if status is not None:
            allowed_status = {"resting", "canceled", "executed"}
            if status not in allowed_status:
                raise ValueError("status must be one of resting, canceled, executed.")

        ts_max = 10_000_000_000
        min_ts = _parse_optional_int(
            arguments,
            "min_ts",
            type_error="min_ts must be an integer.",
            range_error="min_ts must be a non-negative integer.",
            min_value=0,
            max_value=ts_max,
        )
        max_ts = _parse_optional_int(
            arguments,
            "max_ts",
            type_error="max_ts must be an integer.",
            range_error="max_ts must be a non-negative integer.",
            min_value=0,
            max_value=ts_max,
        )
        limit = _parse_optional_int(
            arguments,
            "limit",
            type_error="limit must be an integer.",
            range_error="limit must be between 1 and 200.",
            min_value=1,
            max_value=200,
        )
        subaccount = _parse_optional_int(
            arguments,
            "subaccount",
            type_error="subaccount must be an integer.",
            range_error="subaccount must be between 0 and 32.",
            min_value=0,
            max_value=32,
        )

    orders_list = portfolio_service.get_orders(
        ticker=ticker,
        event_ticker=event_ticker,
        min_ts=min_ts,
        max_ts=max_ts,
        status=status,
        limit=limit,
        cursor=cursor,
        subaccount=subaccount,
    )
    return _serialize_orders_list(orders_list)


def _serialize_orders_list(orders_list: PortfolioOrdersList) -> dict[str, Any]:
    serialized: dict[str, Any] = {"orders": [_serialize_order(item) for item in orders_list.orders]}
    if orders_list.cursor is not None:
        serialized["cursor"] = orders_list.cursor
    return serialized


def _serialize_order(order: PortfolioOrder) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "order_id": order.order_id,
        "user_id": order.user_id,
        "client_order_id": order.client_order_id,
        "ticker": order.ticker,
        "status": order.status,
        "side": order.side,
        "action": order.action,
        "type": order.type,
        "yes_price": order.yes_price,
        "no_price": order.no_price,
        "fill_count": order.fill_count,
        "remaining_count": order.remaining_count,
        "initial_count": order.initial_count,
        "taker_fees": order.taker_fees,
        "maker_fees": order.maker_fees,
        "taker_fill_cost": order.taker_fill_cost,
        "maker_fill_cost": order.maker_fill_cost,
        "queue_position": order.queue_position,
        "yes_price_dollars": order.yes_price_dollars,
        "no_price_dollars": order.no_price_dollars,
        "fill_count_fp": order.fill_count_fp,
        "remaining_count_fp": order.remaining_count_fp,
        "initial_count_fp": order.initial_count_fp,
        "taker_fill_cost_dollars": order.taker_fill_cost_dollars,
        "maker_fill_cost_dollars": order.maker_fill_cost_dollars,
    }

    _maybe(payload, "taker_fees_dollars", order.taker_fees_dollars)
    _maybe(payload, "maker_fees_dollars", order.maker_fees_dollars)
    _maybe(payload, "expiration_time", order.expiration_time)
    _maybe(payload, "created_time", order.created_time)
    _maybe(payload, "last_update_time", order.last_update_time)
    _maybe(payload, "self_trade_prevention_type", order.self_trade_prevention_type)
    _maybe(payload, "order_group_id", order.order_group_id)
    _maybe(payload, "cancel_order_on_pause", order.cancel_order_on_pause)
    _maybe(payload, "subaccount_number", order.subaccount_number)

    return payload


def handle_get_positions(
    portfolio_service: PortfolioService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    cursor: str | None = None
    limit: int | None = None
    count_filter: str | None = None
    ticker: str | None = None
    event_ticker: str | None = None
    subaccount: int | None = None

    if arguments is not None:
        cursor = _parse_optional_str(
            arguments,
            "cursor",
            type_error="cursor must be a string.",
            empty_error="cursor must be a non-empty string.",
        )
        limit = _parse_optional_int(
            arguments,
            "limit",
            type_error="limit must be an integer.",
            range_error="limit must be between 1 and 1000.",
            min_value=1,
            max_value=1000,
        )

        count_filter = _parse_optional_str(
            arguments,
            "count_filter",
            type_error="count_filter must be a string.",
            empty_error="count_filter must be a non-empty string.",
        )
        if count_filter is not None:
            count_filter = _parse_positions_count_filter(count_filter)

        ticker = _parse_optional_str(
            arguments,
            "ticker",
            type_error="ticker must be a string.",
            empty_error="ticker must be a non-empty string.",
        )
        event_ticker = _parse_optional_str(
            arguments,
            "event_ticker",
            type_error="event_ticker must be a string.",
            empty_error="event_ticker must be a non-empty string.",
        )
        subaccount = _parse_optional_int(
            arguments,
            "subaccount",
            type_error="subaccount must be an integer.",
            range_error="subaccount must be between 0 and 32.",
            min_value=0,
            max_value=32,
        )

    positions = portfolio_service.get_positions(
        cursor=cursor,
        limit=limit,
        count_filter=count_filter,
        ticker=ticker,
        event_ticker=event_ticker,
        subaccount=subaccount,
    )
    return _serialize_positions(positions)


def _serialize_positions(positions: PortfolioPositions) -> dict[str, Any]:
    serialized: dict[str, Any] = {
        "market_positions": [
            _serialize_market_position(pos) for pos in positions.market_positions
        ],
        "event_positions": [
            _serialize_event_position(pos) for pos in positions.event_positions
        ],
    }
    if positions.cursor is not None:
        serialized["cursor"] = positions.cursor
    return serialized


def _serialize_market_position(pos: MarketPosition) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ticker": pos.ticker,
        "total_traded": pos.total_traded,
        "total_traded_dollars": pos.total_traded_dollars,
        "position": pos.position,
        "position_fp": pos.position_fp,
        "market_exposure": pos.market_exposure,
        "market_exposure_dollars": pos.market_exposure_dollars,
        "realized_pnl": pos.realized_pnl,
        "realized_pnl_dollars": pos.realized_pnl_dollars,
        "resting_orders_count": pos.resting_orders_count,
        "fees_paid": pos.fees_paid,
        "fees_paid_dollars": pos.fees_paid_dollars,
    }
    _maybe(payload, "last_updated_ts", pos.last_updated_ts)
    return payload


def _serialize_event_position(pos: EventPosition) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_ticker": pos.event_ticker,
        "total_cost": pos.total_cost,
        "total_cost_dollars": pos.total_cost_dollars,
        "total_cost_shares": pos.total_cost_shares,
        "total_cost_shares_fp": pos.total_cost_shares_fp,
        "event_exposure": pos.event_exposure,
        "event_exposure_dollars": pos.event_exposure_dollars,
        "realized_pnl": pos.realized_pnl,
        "realized_pnl_dollars": pos.realized_pnl_dollars,
        "fees_paid": pos.fees_paid,
        "fees_paid_dollars": pos.fees_paid_dollars,
    }
    _maybe(payload, "resting_orders_count", pos.resting_orders_count)
    return payload


def _maybe(payload: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        payload[key] = value


def handle_search_markets(
    metadata_service: MetadataService, arguments: dict[str, Any] | None
) -> dict[str, Any]:
    args = _require_arguments(arguments, "search_markets")
    query = _parse_required_str(
        args,
        "query",
        type_error="query must be a string.",
        empty_error="query must be a non-empty string.",
    )
    limit = (
        _parse_optional_int(
            args,
            "limit",
            type_error="limit must be an integer.",
            range_error="limit must be between 1 and 20.",
            min_value=1,
            max_value=20,
        )
        or 5
    )
    page = min(limit * 3, 60)
    events: list[dict[str, Any]] = []
    seen: set[Any] = set()
    terms = search_terms(query)
    words = [w for w in terms.split() if len(w) >= 3][:3]
    for q in dict.fromkeys(q for q in (terms, query, *words) if q):
        for e in metadata_service.search_events(q, page):
            if e.get("event_ticker") not in seen:
                seen.add(e.get("event_ticker"))
                events.append(e)
    wanted = _stems(query)
    events.sort(key=lambda e: -len(wanted & _stems(_event_text(e))))
    return {"events": [_serialize_search_event(e) for e in events]}


def _stems(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if len(w) < 3 or w in _STOP:
            continue
        for suffix in ("ting", "ing", "es", "s"):
            if w.endswith(suffix) and len(w) - len(suffix) >= 3:
                w = w[: -len(suffix)]
                break
        out.add(w[:5])
    return out


_STOP = {"the", "what", "whats", "are", "will", "for", "and", "odds", "kalshi", "market", "markets", "price", "chance", "game"}


def _event_text(event: dict[str, Any]) -> str:
    parts = [str(event.get("event_title") or ""), str(event.get("event_subtitle") or "")]
    parts += [str(m.get("title") or "") for m in event.get("markets") or [] if isinstance(m, dict)]
    return " ".join(parts)


_MONTHS = (
    "january|february|march|april|may|june|july|august|september|october|november|december|"
    "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
)
_NOISE = re.compile(
    rf"[\u2019']s\b|\b(?:(?:{_MONTHS})\b\.?|\d+(?:st|nd|rd|th)?\b|(?:vs|v|versus|odds|kalshi|market|markets|"
    r"game|games|match|price|prices|chance|chances|the|on|for|of|at|in|and|what|whats|are|is|will|win|wins|"
    r"today|tonight|tomorrow|week|weekend)\b\.?)",
    re.IGNORECASE,
)


def search_terms(query: str) -> str:
    """The names in a query: Kalshi's search matches words, so dates and filler push the right event down."""
    words = re.sub(r"[^\w\s'&.-]", " ", _NOISE.sub(" ", query)).split()
    return " ".join(w for w in words if any(c.isalnum() for c in w))


_SEARCH_MARKETS_PER_EVENT = 10


def _serialize_search_event(event: dict[str, Any]) -> dict[str, Any]:
    series = event.get("series_ticker")
    markets = [m for m in event.get("markets") or [] if isinstance(m, dict)]
    return {
        "event_ticker": event.get("event_ticker"),
        "series_ticker": series,
        "title": event.get("event_title"),
        "subtitle": event.get("event_subtitle"),
        "category": event.get("category"),
        "url": f"https://kalshi.com/markets/{str(series).lower()}" if series else None,
        "markets": [
            {
                "ticker": m.get("ticker"),
                "title": m.get("title") or m.get("yes_subtitle"),
                "yes_bid_dollars": m.get("yes_bid_dollars"),
                "yes_ask_dollars": m.get("yes_ask_dollars"),
                "last_price_dollars": m.get("last_price_dollars"),
                "closes": m.get("close_ts"),
            }
            for m in markets[:_SEARCH_MARKETS_PER_EVENT]
        ],
        "more_markets": max(len(markets) - _SEARCH_MARKETS_PER_EVENT, 0),
    }
