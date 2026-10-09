"""Kalshi HTTP client wrappers."""

from __future__ import annotations

import base64
import json
import logging
import random
import time
from typing import Any
from urllib import parse
from urllib import error, request

from .models import (
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
from .settings import Settings

LOGGER = logging.getLogger(__name__)


class KalshiClientError(RuntimeError):
    """Raised when Kalshi API requests fail."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class KalshiClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.base_url
        self._timeout_seconds = settings.timeout_seconds
        self._api_key_id = settings.api_key_id
        self._api_key_path = settings.api_key_path
        self._api_key_pem = settings.api_key_pem
        self._cached_private_key: Any | None = None

    def get_tags_for_series_categories(self) -> TagsByCategories:
        """Return tags grouped by series categories."""
        payload = self._get_json("/search/tags_by_categories")
        tags = payload.get("tags_by_categories")

        if not isinstance(tags, dict):
            LOGGER.error(
                "Unexpected tags-by-categories payload: expected object at 'tags_by_categories', got=%s",
                self._describe_value(tags),
            )
            raise KalshiClientError(
                "Unexpected response shape from Kalshi API: "
                "missing 'tags_by_categories' object."
            )

        normalized: dict[str, list[str]] = {}
        for category, values in tags.items():
            if isinstance(category, str) and isinstance(values, list):
                normalized[category] = [item for item in values if isinstance(item, str)]

        return TagsByCategories(tags_by_categories=normalized)

    def get_api_key_scopes(self) -> list[str]:
        """Return the scopes of the key this client signs with."""
        payload = self._get_json("/api_keys", authenticated=True)
        for key in payload.get("api_keys") or []:
            if isinstance(key, dict) and key.get("api_key_id") == self._api_key_id:
                scopes = key.get("scopes")
                return [s for s in scopes if isinstance(s, str)] if isinstance(scopes, list) else []
        raise KalshiClientError("Kalshi did not list this API key.")

    def get_balance(self) -> PortfolioBalance:
        """Return authenticated user account balance."""
        payload = self._get_json("/portfolio/balance", authenticated=True)

        balance = self._require_int_field(payload, "balance", endpoint="/portfolio/balance")
        portfolio_value = self._require_int_field(
            payload, "portfolio_value", endpoint="/portfolio/balance"
        )
        updated_ts = self._require_int_field(payload, "updated_ts", endpoint="/portfolio/balance")
        return PortfolioBalance(
            balance=balance,
            portfolio_value=portfolio_value,
            updated_ts=updated_ts,
        )

    def get_subaccount_balances(self) -> SubaccountBalancesList:
        """Return balances for all subaccounts."""
        endpoint = "/portfolio/subaccounts/balances"
        payload = self._get_json(endpoint, authenticated=True)

        raw_balances = payload.get("subaccount_balances")
        if not isinstance(raw_balances, list):
            LOGGER.error(
                "Unexpected %s payload: expected list at 'subaccount_balances', got=%s keys=%s",
                endpoint,
                self._describe_value(raw_balances),
                sorted(payload.keys()),
            )
            raise KalshiClientError(
                "Unexpected response shape from Kalshi API: "
                "missing 'subaccount_balances' array."
            )

        parsed: list[SubaccountBalance] = []
        for index, item in enumerate(raw_balances):
            if not isinstance(item, dict):
                LOGGER.warning(
                    "Skipping subaccount_balances[%s]: expected object, got %s",
                    index,
                    self._describe_value(item),
                )
                continue

            subaccount_number = item.get("subaccount_number")
            if isinstance(subaccount_number, bool) or not isinstance(subaccount_number, int):
                LOGGER.warning(
                    "Skipping subaccount_balances[%s]: expected 'subaccount_number' as int, got %s",
                    index,
                    self._describe_value(subaccount_number),
                )
                continue

            balance = item.get("balance")
            if not isinstance(balance, str):
                LOGGER.warning(
                    "Skipping subaccount_balances[%s]: expected 'balance' as string, got %s",
                    index,
                    self._describe_value(balance),
                )
                continue

            updated_ts = item.get("updated_ts")
            if isinstance(updated_ts, bool) or not isinstance(updated_ts, int):
                LOGGER.warning(
                    "Skipping subaccount_balances[%s]: expected 'updated_ts' as int, got %s",
                    index,
                    self._describe_value(updated_ts),
                )
                continue

            parsed.append(
                SubaccountBalance(
                    subaccount_number=subaccount_number,
                    balance=balance,
                    updated_ts=updated_ts,
                )
            )

        return SubaccountBalancesList(subaccount_balances=parsed)

    def get_orders(
        self,
        *,
        ticker: str | None = None,
        event_ticker: str | None = None,
        min_ts: int | None = None,
        max_ts: int | None = None,
        status: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        subaccount: int | None = None,
    ) -> PortfolioOrdersList:
        """Return portfolio orders from Kalshi (GET /portfolio/orders)."""
        endpoint = "/portfolio/orders"
        params: dict[str, str] = {}
        if ticker is not None:
            params["ticker"] = ticker
        if event_ticker is not None:
            params["event_ticker"] = event_ticker
        if min_ts is not None:
            params["min_ts"] = str(min_ts)
        if max_ts is not None:
            params["max_ts"] = str(max_ts)
        if status is not None:
            params["status"] = status
        if limit is not None:
            params["limit"] = str(limit)
        if cursor is not None:
            params["cursor"] = cursor
        if subaccount is not None:
            params["subaccount"] = str(subaccount)

        path = endpoint
        if params:
            path = f"{path}?{parse.urlencode(params)}"

        payload = self._get_json(path, authenticated=True)

        raw_orders = payload.get("orders")
        if not isinstance(raw_orders, list):
            LOGGER.error(
                "Unexpected %s payload: expected list at 'orders', got=%s keys=%s",
                endpoint,
                self._describe_value(raw_orders),
                sorted(payload.keys()),
            )
            raise KalshiClientError(
                "Unexpected response shape from Kalshi API: missing 'orders' array."
            )

        parsed: list[PortfolioOrder] = []
        for index, item in enumerate(raw_orders):
            order = self._parse_order(item, index)
            if order is not None:
                parsed.append(order)

        next_cursor = payload.get("cursor")
        if next_cursor is not None and not isinstance(next_cursor, str):
            LOGGER.warning(
                "Ignoring unexpected 'cursor' type in orders response: %s",
                self._describe_value(next_cursor),
            )
            next_cursor = None
        if next_cursor == "":
            next_cursor = None

        return PortfolioOrdersList(orders=parsed, cursor=next_cursor)

    def get_order(self, order_id: str) -> PortfolioOrder:
        """Return a single portfolio order by ID from Kalshi."""
        path = f"/portfolio/orders/{parse.quote(order_id, safe='')}"
        payload = self._get_json(path, authenticated=True)

        raw_order = payload.get("order")
        if not isinstance(raw_order, dict):
            LOGGER.error(
                "GET /portfolio/orders/%s: 'order' is not an object: %s",
                order_id,
                self._describe_value(raw_order),
            )
            raise KalshiClientError(
                f"GET /portfolio/orders/{order_id}: expected 'order' object in response."
            )

        order = self._parse_order(raw_order, 0)
        if order is None:
            raise KalshiClientError(
                f"GET /portfolio/orders/{order_id}: unable to parse order from response."
            )
        return order

    def get_positions(
        self,
        *,
        cursor: str | None = None,
        limit: int | None = None,
        count_filter: str | None = None,
        ticker: str | None = None,
        event_ticker: str | None = None,
        subaccount: int | None = None,
    ) -> PortfolioPositions:
        """Return portfolio positions from Kalshi (GET /portfolio/positions)."""
        endpoint = "/portfolio/positions"
        params: dict[str, str] = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = str(limit)
        if count_filter is not None:
            params["count_filter"] = count_filter
        if ticker is not None:
            params["ticker"] = ticker
        if event_ticker is not None:
            params["event_ticker"] = event_ticker
        if subaccount is not None:
            params["subaccount"] = str(subaccount)

        path = endpoint
        if params:
            path = f"{path}?{parse.urlencode(params)}"

        payload = self._get_json(path, authenticated=True)

        # Parse market_positions
        raw_market_positions = payload.get("market_positions")
        if not isinstance(raw_market_positions, list):
            LOGGER.error(
                "Unexpected %s payload: expected list at 'market_positions', got=%s keys=%s",
                endpoint,
                self._describe_value(raw_market_positions),
                sorted(payload.keys()),
            )
            raise KalshiClientError(
                "Unexpected response shape from Kalshi API: missing 'market_positions' array."
            )

        parsed_market_positions: list[MarketPosition] = []
        for index, item in enumerate(raw_market_positions):
            mp = self._parse_market_position(item, index)
            if mp is not None:
                parsed_market_positions.append(mp)

        # Parse event_positions
        raw_event_positions = payload.get("event_positions")
        if not isinstance(raw_event_positions, list):
            LOGGER.error(
                "Unexpected %s payload: expected list at 'event_positions', got=%s keys=%s",
                endpoint,
                self._describe_value(raw_event_positions),
                sorted(payload.keys()),
            )
            raise KalshiClientError(
                "Unexpected response shape from Kalshi API: missing 'event_positions' array."
            )

        parsed_event_positions: list[EventPosition] = []
        for index, item in enumerate(raw_event_positions):
            ep = self._parse_event_position(item, index)
            if ep is not None:
                parsed_event_positions.append(ep)

        # Parse cursor
        next_cursor = payload.get("cursor")
        if next_cursor is not None and not isinstance(next_cursor, str):
            LOGGER.warning(
                "Ignoring unexpected 'cursor' type in positions response: %s",
                self._describe_value(next_cursor),
            )
            next_cursor = None
        if next_cursor == "":
            next_cursor = None

        return PortfolioPositions(
            cursor=next_cursor,
            market_positions=parsed_market_positions,
            event_positions=parsed_event_positions,
        )

    def _parse_market_position(self, raw: Any, index: int) -> MarketPosition | None:
        if not isinstance(raw, dict):
            LOGGER.warning(
                "Skipping market_positions[%s]: expected object, got %s",
                index,
                self._describe_value(raw),
            )
            return None

        required_string_fields = (
            "ticker",
            "total_traded_dollars",
            "position_fp",
            "market_exposure_dollars",
            "realized_pnl_dollars",
            "fees_paid_dollars",
        )
        string_values: dict[str, str] = {}
        for field_name in required_string_fields:
            value = raw.get(field_name)
            if not isinstance(value, str):
                LOGGER.warning(
                    "Skipping market_positions[%s]: expected '%s' as string, got %s",
                    index, field_name, self._describe_value(value),
                )
                return None
            string_values[field_name] = value

        required_int_fields = ("total_traded", "position", "market_exposure",
                               "realized_pnl", "resting_orders_count", "fees_paid")
        int_values: dict[str, int] = {}
        for field_name in required_int_fields:
            value = raw.get(field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                LOGGER.warning(
                    "Skipping market_positions[%s]: expected '%s' as int, got %s",
                    index, field_name, self._describe_value(value),
                )
                return None
            int_values[field_name] = value

        last_updated_ts = raw.get("last_updated_ts")
        if last_updated_ts is not None and not isinstance(last_updated_ts, str):
            LOGGER.warning(
                "Ignoring market_positions[%s].last_updated_ts with unexpected type %s",
                index,
                self._describe_value(last_updated_ts),
            )
            last_updated_ts = None

        return MarketPosition(
            ticker=string_values["ticker"],
            total_traded=int_values["total_traded"],
            total_traded_dollars=string_values["total_traded_dollars"],
            position=int_values["position"],
            position_fp=string_values["position_fp"],
            market_exposure=int_values["market_exposure"],
            market_exposure_dollars=string_values["market_exposure_dollars"],
            realized_pnl=int_values["realized_pnl"],
            realized_pnl_dollars=string_values["realized_pnl_dollars"],
            resting_orders_count=int_values["resting_orders_count"],
            fees_paid=int_values["fees_paid"],
            fees_paid_dollars=string_values["fees_paid_dollars"],
            last_updated_ts=last_updated_ts,
        )

    def _parse_event_position(self, raw: Any, index: int) -> EventPosition | None:
        if not isinstance(raw, dict):
            LOGGER.warning(
                "Skipping event_positions[%s]: expected object, got %s",
                index,
                self._describe_value(raw),
            )
            return None

        required_string_fields = ("event_ticker", "total_cost_dollars", "total_cost_shares_fp",
                                  "event_exposure_dollars", "realized_pnl_dollars",
                                  "fees_paid_dollars")
        string_values: dict[str, str] = {}
        for field_name in required_string_fields:
            value = raw.get(field_name)
            if not isinstance(value, str):
                LOGGER.warning(
                    "Skipping event_positions[%s]: expected '%s' as string, got %s",
                    index, field_name, self._describe_value(value),
                )
                return None
            string_values[field_name] = value

        required_int_fields = ("total_cost", "total_cost_shares", "event_exposure",
                               "realized_pnl", "fees_paid")
        int_values: dict[str, int] = {}
        for field_name in required_int_fields:
            value = raw.get(field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                LOGGER.warning(
                    "Skipping event_positions[%s]: expected '%s' as int, got %s",
                    index, field_name, self._describe_value(value),
                )
                return None
            int_values[field_name] = value

        resting_orders_count = raw.get("resting_orders_count")
        if resting_orders_count is not None:
            if isinstance(resting_orders_count, bool) or not isinstance(resting_orders_count, int):
                LOGGER.warning(
                    "Ignoring event_positions[%s].resting_orders_count with unexpected type %s",
                    index,
                    self._describe_value(resting_orders_count),
                )
                resting_orders_count = None

        return EventPosition(
            event_ticker=string_values["event_ticker"],
            total_cost=int_values["total_cost"],
            total_cost_dollars=string_values["total_cost_dollars"],
            total_cost_shares=int_values["total_cost_shares"],
            total_cost_shares_fp=string_values["total_cost_shares_fp"],
            event_exposure=int_values["event_exposure"],
            event_exposure_dollars=string_values["event_exposure_dollars"],
            realized_pnl=int_values["realized_pnl"],
            realized_pnl_dollars=string_values["realized_pnl_dollars"],
            fees_paid=int_values["fees_paid"],
            fees_paid_dollars=string_values["fees_paid_dollars"],
            resting_orders_count=resting_orders_count,
        )

    def _parse_order(self, raw_order: Any, index: int) -> PortfolioOrder | None:
        if not isinstance(raw_order, dict):
            LOGGER.warning(
                "Skipping orders[%s]: expected object, got %s",
                index,
                self._describe_value(raw_order),
            )
            return None

        required_string_fields = (
            "order_id",
            "user_id",
            "client_order_id",
            "ticker",
            "status",
            "side",
            "action",
            "type",
        )
        string_values: dict[str, str] = {}
        for field_name in required_string_fields:
            value = raw_order.get(field_name)
            if not isinstance(value, str):
                LOGGER.warning(
                    "Skipping orders[%s]: expected '%s' as string, got %s",
                    index,
                    field_name,
                    self._describe_value(value),
                )
                return None
            string_values[field_name] = value

        required_int_fields = (
            "yes_price",
            "no_price",
            "fill_count",
            "remaining_count",
            "initial_count",
            "taker_fees",
            "maker_fees",
            "taker_fill_cost",
            "maker_fill_cost",
            "queue_position",
        )
        int_values: dict[str, int] = {}
        for field_name in required_int_fields:
            value = raw_order.get(field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                LOGGER.warning(
                    "Skipping orders[%s]: expected '%s' as int, got %s",
                    index,
                    field_name,
                    self._describe_value(value),
                )
                return None
            int_values[field_name] = value

        required_dollar_fields = (
            "yes_price_dollars",
            "no_price_dollars",
            "fill_count_fp",
            "remaining_count_fp",
            "initial_count_fp",
            "taker_fill_cost_dollars",
            "maker_fill_cost_dollars",
        )
        dollar_values: dict[str, str] = {}
        for field_name in required_dollar_fields:
            value = raw_order.get(field_name)
            if not isinstance(value, str):
                LOGGER.warning(
                    "Skipping orders[%s]: expected '%s' as string, got %s",
                    index,
                    field_name,
                    self._describe_value(value),
                )
                return None
            dollar_values[field_name] = value

        # Optional string fields
        opt_taker_fees_dollars = self._optional_order_str(raw_order, "taker_fees_dollars", index)
        opt_maker_fees_dollars = self._optional_order_str(raw_order, "maker_fees_dollars", index)
        opt_expiration_time = self._optional_order_str(raw_order, "expiration_time", index)
        opt_created_time = self._optional_order_str(raw_order, "created_time", index)
        opt_last_update_time = self._optional_order_str(raw_order, "last_update_time", index)
        opt_self_trade_prevention_type = self._optional_order_str(
            raw_order, "self_trade_prevention_type", index
        )
        opt_order_group_id = self._optional_order_str(raw_order, "order_group_id", index)

        # Optional bool field
        opt_cancel_order_on_pause = self._optional_order_bool(
            raw_order, "cancel_order_on_pause", index
        )

        # Optional int field
        opt_subaccount_number = self._optional_order_int(raw_order, "subaccount_number", index)

        return PortfolioOrder(
            order_id=string_values["order_id"],
            user_id=string_values["user_id"],
            client_order_id=string_values["client_order_id"],
            ticker=string_values["ticker"],
            status=string_values["status"],
            side=string_values["side"],
            action=string_values["action"],
            type=string_values["type"],
            yes_price=int_values["yes_price"],
            no_price=int_values["no_price"],
            fill_count=int_values["fill_count"],
            remaining_count=int_values["remaining_count"],
            initial_count=int_values["initial_count"],
            taker_fees=int_values["taker_fees"],
            maker_fees=int_values["maker_fees"],
            taker_fill_cost=int_values["taker_fill_cost"],
            maker_fill_cost=int_values["maker_fill_cost"],
            queue_position=int_values["queue_position"],
            yes_price_dollars=dollar_values["yes_price_dollars"],
            no_price_dollars=dollar_values["no_price_dollars"],
            fill_count_fp=dollar_values["fill_count_fp"],
            remaining_count_fp=dollar_values["remaining_count_fp"],
            initial_count_fp=dollar_values["initial_count_fp"],
            taker_fill_cost_dollars=dollar_values["taker_fill_cost_dollars"],
            maker_fill_cost_dollars=dollar_values["maker_fill_cost_dollars"],
            taker_fees_dollars=opt_taker_fees_dollars,
            maker_fees_dollars=opt_maker_fees_dollars,
            expiration_time=opt_expiration_time,
            created_time=opt_created_time,
            last_update_time=opt_last_update_time,
            self_trade_prevention_type=opt_self_trade_prevention_type,
            order_group_id=opt_order_group_id,
            cancel_order_on_pause=opt_cancel_order_on_pause,
            subaccount_number=opt_subaccount_number,
        )

    def _optional_order_str(self, raw: dict[str, Any], key: str, index: int) -> str | None:
        value = raw.get(key)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        LOGGER.warning(
            "Ignoring unexpected '%s' type in orders[%s]: %s",
            key,
            index,
            self._describe_value(value),
        )
        return None

    def _optional_order_int(self, raw: dict[str, Any], key: str, index: int) -> int | None:
        value = raw.get(key)
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            LOGGER.warning(
                "Ignoring unexpected '%s' type in orders[%s]: %s",
                key,
                index,
                self._describe_value(value),
            )
            return None
        return value

    def _optional_order_bool(self, raw: dict[str, Any], key: str, index: int) -> bool | None:
        value = raw.get(key)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        LOGGER.warning(
            "Ignoring unexpected '%s' type in orders[%s]: %s",
            key,
            index,
            self._describe_value(value),
        )
        return None

    def get_series_list(
        self,
        category: str | None = None,
        tags: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
        include_product_metadata: bool = False,
        include_volume: bool = False,
    ) -> SeriesList:
        """Return market series list from Kalshi."""
        params: dict[str, str] = {}
        if category is not None:
            params["category"] = category
        if tags is not None:
            params["tags"] = tags
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = str(limit)
        if include_product_metadata:
            params["include_product_metadata"] = "true"
        if include_volume:
            params["include_volume"] = "true"

        path = "/series"
        if params:
            path = f"{path}?{parse.urlencode(params)}"

        payload = self._get_json(path)
        series_items = payload.get("series")
        if not isinstance(series_items, list):
            LOGGER.error(
                "Unexpected series-list payload: expected list at 'series', got=%s keys=%s",
                self._describe_value(series_items),
                sorted(payload.keys()),
            )
            raise KalshiClientError(
                "Unexpected response shape from Kalshi API: missing 'series' array."
            )

        parsed_series: list[Series] = []
        for index, raw_series in enumerate(series_items):
            parsed = self._parse_series(raw_series, index)
            if parsed is not None:
                parsed_series.append(parsed)

        cursor = payload.get("cursor")
        if cursor is not None and not isinstance(cursor, str):
            LOGGER.warning(
                "Ignoring unexpected 'cursor' type in series list response: %s",
                self._describe_value(cursor),
            )
            cursor = None
        # Kalshi may return an empty string cursor when pagination is complete.
        if cursor == "":
            cursor = None

        return SeriesList(series=parsed_series, cursor=cursor)

    def get_markets(
        self,
        *,
        cursor: str | None = None,
        limit: int | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        tickers: str | None = None,
        status: str | None = None,
        mve_filter: str | None = None,
        min_created_ts: int | None = None,
        max_created_ts: int | None = None,
        min_updated_ts: int | None = None,
        min_close_ts: int | None = None,
        max_close_ts: int | None = None,
        min_settled_ts: int | None = None,
        max_settled_ts: int | None = None,
    ) -> MarketsList:
        """Return markets list from Kalshi (GET /markets)."""
        params: dict[str, str] = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = str(limit)
        if event_ticker is not None:
            params["event_ticker"] = event_ticker
        if series_ticker is not None:
            params["series_ticker"] = series_ticker
        if tickers is not None:
            params["tickers"] = tickers
        if status is not None:
            params["status"] = status
        if mve_filter is not None:
            params["mve_filter"] = mve_filter

        if min_created_ts is not None:
            params["min_created_ts"] = str(min_created_ts)
        if max_created_ts is not None:
            params["max_created_ts"] = str(max_created_ts)
        if min_updated_ts is not None:
            params["min_updated_ts"] = str(min_updated_ts)
        if min_close_ts is not None:
            params["min_close_ts"] = str(min_close_ts)
        if max_close_ts is not None:
            params["max_close_ts"] = str(max_close_ts)
        if min_settled_ts is not None:
            params["min_settled_ts"] = str(min_settled_ts)
        if max_settled_ts is not None:
            params["max_settled_ts"] = str(max_settled_ts)

        path = "/markets"
        if params:
            path = f"{path}?{parse.urlencode(params)}"

        payload = self._get_json(path)
        market_items = payload.get("markets")
        if not isinstance(market_items, list):
            LOGGER.error(
                "Unexpected markets payload: expected list at 'markets', got=%s keys=%s",
                self._describe_value(market_items),
                sorted(payload.keys()),
            )
            raise KalshiClientError(
                "Unexpected response shape from Kalshi API: missing 'markets' array."
            )

        parsed_markets: list[Market] = []
        for index, raw_market in enumerate(market_items):
            parsed = self._parse_market(raw_market, index)
            if parsed is not None:
                parsed_markets.append(parsed)

        next_cursor = payload.get("cursor")
        if next_cursor is not None and not isinstance(next_cursor, str):
            LOGGER.warning(
                "Ignoring unexpected 'cursor' type in markets response: %s",
                self._describe_value(next_cursor),
            )
            next_cursor = None
        # Kalshi may return an empty string cursor when pagination is complete.
        if next_cursor == "":
            next_cursor = None

        return MarketsList(markets=parsed_markets, cursor=next_cursor)

    def _parse_series(self, raw_series: Any, index: int) -> Series | None:
        if not isinstance(raw_series, dict):
            LOGGER.warning(
                "Skipping series[%s]: expected object, got %s",
                index,
                self._describe_value(raw_series),
            )
            return None

        required_string_fields = (
            "ticker",
            "frequency",
            "title",
            "category",
            "contract_url",
            "contract_terms_url",
            "fee_type",
        )
        string_values: dict[str, str] = {}
        for field_name in required_string_fields:
            value = raw_series.get(field_name)
            if not isinstance(value, str):
                LOGGER.warning(
                    "Skipping series[%s]: expected '%s' as string, got %s",
                    index,
                    field_name,
                    self._describe_value(value),
                )
                return None
            string_values[field_name] = value

        raw_fee_multiplier = raw_series.get("fee_multiplier")
        if isinstance(raw_fee_multiplier, bool) or not isinstance(raw_fee_multiplier, (int, float)):
            LOGGER.warning(
                "Skipping series[%s]: expected 'fee_multiplier' as number, got %s",
                index,
                self._describe_value(raw_fee_multiplier),
            )
            return None

        raw_tags = raw_series.get("tags")
        tags: list[str] | None
        if raw_tags is None:
            tags = None
        elif isinstance(raw_tags, list):
            tags = [tag for tag in raw_tags if isinstance(tag, str)]
            if len(tags) != len(raw_tags):
                LOGGER.warning(
                    "Dropped non-string tag values in series[%s]; before=%s after=%s",
                    index,
                    len(raw_tags),
                    len(tags),
                )
        else:
            # Kalshi occasionally returns null here; treat other unexpected types as absent.
            LOGGER.warning(
                "Unexpected 'tags' type in series[%s]; got %s",
                index,
                self._describe_value(raw_tags),
            )
            tags = None

        settlement_sources = self._parse_settlement_sources(
            raw_series.get("settlement_sources"), index
        )
        if settlement_sources is None:
            return None

        raw_additional_prohibitions = raw_series.get("additional_prohibitions")
        additional_prohibitions: list[str] | None
        if raw_additional_prohibitions is None:
            additional_prohibitions = None
        elif isinstance(raw_additional_prohibitions, list):
            additional_prohibitions = [
                value for value in raw_additional_prohibitions if isinstance(value, str)
            ]
            if len(additional_prohibitions) != len(raw_additional_prohibitions):
                LOGGER.warning(
                    "Dropped non-string additional_prohibitions in series[%s]; before=%s after=%s",
                    index,
                    len(raw_additional_prohibitions),
                    len(additional_prohibitions),
                )
        else:
            LOGGER.warning(
                "Unexpected 'additional_prohibitions' type in series[%s]; got %s",
                index,
                self._describe_value(raw_additional_prohibitions),
            )
            additional_prohibitions = None

        product_metadata = raw_series.get("product_metadata")
        if product_metadata is not None and not isinstance(product_metadata, dict):
            LOGGER.warning(
                "Ignoring unexpected 'product_metadata' type in series[%s]: %s",
                index,
                self._describe_value(product_metadata),
            )
            product_metadata = None

        volume = raw_series.get("volume")
        if isinstance(volume, bool) or (volume is not None and not isinstance(volume, int)):
            LOGGER.warning(
                "Ignoring unexpected 'volume' type in series[%s]: %s",
                index,
                self._describe_value(volume),
            )
            volume = None

        volume_fp = raw_series.get("volume_fp")
        if volume_fp is not None and not isinstance(volume_fp, str):
            LOGGER.warning(
                "Ignoring unexpected 'volume_fp' type in series[%s]: %s",
                index,
                self._describe_value(volume_fp),
            )
            volume_fp = None

        return Series(
            ticker=string_values["ticker"],
            frequency=string_values["frequency"],
            title=string_values["title"],
            category=string_values["category"],
            tags=tags,
            settlement_sources=settlement_sources,
            contract_url=string_values["contract_url"],
            contract_terms_url=string_values["contract_terms_url"],
            fee_type=string_values["fee_type"],
            fee_multiplier=float(raw_fee_multiplier),
            additional_prohibitions=additional_prohibitions,
            product_metadata=product_metadata,
            volume=volume,
            volume_fp=volume_fp,
        )

    def _parse_market(self, raw_market: Any, index: int) -> Market | None:
        if not isinstance(raw_market, dict):
            LOGGER.warning(
                "Skipping markets[%s]: expected object, got %s",
                index,
                self._describe_value(raw_market),
            )
            return None

        required_string_fields = (
            "ticker",
            "event_ticker",
            "market_type",
            "title",
            "status",
        )
        string_values: dict[str, str] = {}
        for field_name in required_string_fields:
            value = raw_market.get(field_name)
            if not isinstance(value, str):
                LOGGER.warning(
                    "Skipping markets[%s]: expected '%s' as string, got %s",
                    index,
                    field_name,
                    self._describe_value(value),
                )
                return None
            string_values[field_name] = value

        price_ranges = self._parse_price_ranges(raw_market.get("price_ranges"), index)
        mve_selected_legs = self._parse_mve_selected_legs(
            raw_market.get("mve_selected_legs"), index
        )

        custom_strike = raw_market.get("custom_strike")
        if custom_strike is not None and not isinstance(custom_strike, dict):
            LOGGER.warning(
                "Ignoring unexpected 'custom_strike' type in markets[%s]: %s",
                index,
                self._describe_value(custom_strike),
            )
            custom_strike = None
        if isinstance(custom_strike, dict):
            # Ensure string keys; values remain arbitrary JSON.
            custom_strike = {k: v for k, v in custom_strike.items() if isinstance(k, str)}

        tick_size = raw_market.get("tick_size")
        if isinstance(tick_size, bool) or (tick_size is not None and not isinstance(tick_size, int)):
            LOGGER.warning(
                "Ignoring unexpected 'tick_size' type in markets[%s]: %s",
                index,
                self._describe_value(tick_size),
            )
            tick_size = None

        return Market(
            ticker=string_values["ticker"],
            event_ticker=string_values["event_ticker"],
            market_type=string_values["market_type"],
            title=string_values["title"],
            subtitle=self._optional_str(raw_market, "subtitle", index=index),
            status=string_values["status"],
            series_ticker=self._optional_str(raw_market, "series_ticker", index=index),
            yes_sub_title=self._optional_str(raw_market, "yes_sub_title", index=index),
            no_sub_title=self._optional_str(raw_market, "no_sub_title", index=index),
            created_time=self._optional_str(raw_market, "created_time", index=index),
            updated_time=self._optional_str(raw_market, "updated_time", index=index),
            open_time=self._optional_str(raw_market, "open_time", index=index),
            close_time=self._optional_str(raw_market, "close_time", index=index),
            expiration_time=self._optional_str(raw_market, "expiration_time", index=index),
            latest_expiration_time=self._optional_str(
                raw_market, "latest_expiration_time", index=index
            ),
            response_price_units=self._optional_str(
                raw_market, "response_price_units", index=index
            ),
            settlement_timer_seconds=self._optional_int(
                raw_market, "settlement_timer_seconds", index=index
            ),
            yes_bid=self._optional_int(raw_market, "yes_bid", index=index),
            yes_ask=self._optional_int(raw_market, "yes_ask", index=index),
            no_bid=self._optional_int(raw_market, "no_bid", index=index),
            no_ask=self._optional_int(raw_market, "no_ask", index=index),
            last_price=self._optional_int(raw_market, "last_price", index=index),
            volume=self._optional_int(raw_market, "volume", index=index),
            volume_24h=self._optional_int(raw_market, "volume_24h", index=index),
            open_interest=self._optional_int(raw_market, "open_interest", index=index),
            notional_value=self._optional_int(raw_market, "notional_value", index=index),
            previous_yes_bid=self._optional_int(raw_market, "previous_yes_bid", index=index),
            previous_yes_ask=self._optional_int(raw_market, "previous_yes_ask", index=index),
            previous_price=self._optional_int(raw_market, "previous_price", index=index),
            liquidity=self._optional_int(raw_market, "liquidity", index=index),
            tick_size=tick_size,
            settlement_value=self._optional_int(raw_market, "settlement_value", index=index),
            floor_strike=self._optional_float(raw_market, "floor_strike", index=index),
            cap_strike=self._optional_float(raw_market, "cap_strike", index=index),
            yes_bid_dollars=self._optional_str(raw_market, "yes_bid_dollars", index=index),
            yes_ask_dollars=self._optional_str(raw_market, "yes_ask_dollars", index=index),
            no_bid_dollars=self._optional_str(raw_market, "no_bid_dollars", index=index),
            no_ask_dollars=self._optional_str(raw_market, "no_ask_dollars", index=index),
            last_price_dollars=self._optional_str(raw_market, "last_price_dollars", index=index),
            volume_fp=self._optional_str(raw_market, "volume_fp", index=index),
            volume_24h_fp=self._optional_str(raw_market, "volume_24h_fp", index=index),
            open_interest_fp=self._optional_str(raw_market, "open_interest_fp", index=index),
            notional_value_dollars=self._optional_str(
                raw_market, "notional_value_dollars", index=index
            ),
            previous_yes_bid_dollars=self._optional_str(
                raw_market, "previous_yes_bid_dollars", index=index
            ),
            previous_yes_ask_dollars=self._optional_str(
                raw_market, "previous_yes_ask_dollars", index=index
            ),
            previous_price_dollars=self._optional_str(
                raw_market, "previous_price_dollars", index=index
            ),
            liquidity_dollars=self._optional_str(raw_market, "liquidity_dollars", index=index),
            settlement_value_dollars=self._optional_str(
                raw_market, "settlement_value_dollars", index=index
            ),
            result=self._optional_str(raw_market, "result", index=index),
            can_close_early=self._optional_bool(raw_market, "can_close_early", index=index),
            expiration_value=self._optional_str(raw_market, "expiration_value", index=index),
            rules_primary=self._optional_str(raw_market, "rules_primary", index=index),
            rules_secondary=self._optional_str(raw_market, "rules_secondary", index=index),
            price_level_structure=self._optional_str(
                raw_market, "price_level_structure", index=index
            ),
            price_ranges=price_ranges,
            expected_expiration_time=self._optional_str(
                raw_market, "expected_expiration_time", index=index
            ),
            settlement_ts=self._optional_str(raw_market, "settlement_ts", index=index),
            fee_waiver_expiration_time=self._optional_str(
                raw_market, "fee_waiver_expiration_time", index=index
            ),
            early_close_condition=self._optional_str(
                raw_market, "early_close_condition", index=index
            ),
            strike_type=self._optional_str(raw_market, "strike_type", index=index),
            functional_strike=self._optional_str(raw_market, "functional_strike", index=index),
            custom_strike=custom_strike,
            mve_collection_ticker=self._optional_str(
                raw_market, "mve_collection_ticker", index=index
            ),
            mve_selected_legs=mve_selected_legs,
            primary_participant_key=self._optional_str(
                raw_market, "primary_participant_key", index=index
            ),
            is_provisional=self._optional_bool(raw_market, "is_provisional", index=index),
        )

    def _optional_str(self, raw: dict[str, Any], key: str, *, index: int) -> str | None:
        value = raw.get(key)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        LOGGER.warning(
            "Ignoring unexpected '%s' type in markets[%s]: %s",
            key,
            index,
            self._describe_value(value),
        )
        return None

    def _optional_int(self, raw: dict[str, Any], key: str, *, index: int) -> int | None:
        value = raw.get(key)
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            LOGGER.warning(
                "Ignoring unexpected '%s' type in markets[%s]: %s",
                key,
                index,
                self._describe_value(value),
            )
            return None
        return value

    def _optional_float(self, raw: dict[str, Any], key: str, *, index: int) -> float | None:
        value = raw.get(key)
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            LOGGER.warning(
                "Ignoring unexpected '%s' type in markets[%s]: %s",
                key,
                index,
                self._describe_value(value),
            )
            return None
        return float(value)

    def _optional_bool(self, raw: dict[str, Any], key: str, *, index: int) -> bool | None:
        value = raw.get(key)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        LOGGER.warning(
            "Ignoring unexpected '%s' type in markets[%s]: %s",
            key,
            index,
            self._describe_value(value),
        )
        return None

    def _parse_price_ranges(self, raw_value: Any, index: int) -> list[PriceRange] | None:
        if raw_value is None:
            return None
        if not isinstance(raw_value, list):
            LOGGER.warning(
                "Ignoring unexpected 'price_ranges' type in markets[%s]: %s",
                index,
                self._describe_value(raw_value),
            )
            return None
        parsed: list[PriceRange] = []
        for range_index, item in enumerate(raw_value):
            if not isinstance(item, dict):
                LOGGER.warning(
                    "Skipping invalid price_ranges item in markets[%s] at index %s: %s",
                    index,
                    range_index,
                    self._describe_value(item),
                )
                continue
            start = item.get("start")
            end = item.get("end")
            step = item.get("step")
            if not isinstance(start, str) or not isinstance(end, str) or not isinstance(step, str):
                LOGGER.warning(
                    "Skipping invalid price_ranges item in markets[%s] at index %s: %s",
                    index,
                    range_index,
                    self._describe_value(item),
                )
                continue
            parsed.append(PriceRange(start=start, end=end, step=step))
        return parsed

    def _parse_mve_selected_legs(
        self, raw_value: Any, index: int
    ) -> list[MveSelectedLeg] | None:
        if raw_value is None:
            return None
        if not isinstance(raw_value, list):
            LOGGER.warning(
                "Ignoring unexpected 'mve_selected_legs' type in markets[%s]: %s",
                index,
                self._describe_value(raw_value),
            )
            return None
        parsed: list[MveSelectedLeg] = []
        for leg_index, item in enumerate(raw_value):
            if not isinstance(item, dict):
                LOGGER.warning(
                    "Skipping invalid mve_selected_legs item in markets[%s] at index %s: %s",
                    index,
                    leg_index,
                    self._describe_value(item),
                )
                continue
            event_ticker = item.get("event_ticker")
            market_ticker = item.get("market_ticker")
            side = item.get("side")
            if (
                not isinstance(event_ticker, str)
                or not isinstance(market_ticker, str)
                or not isinstance(side, str)
            ):
                LOGGER.warning(
                    "Skipping invalid mve_selected_legs item in markets[%s] at index %s: %s",
                    index,
                    leg_index,
                    self._describe_value(item),
                )
                continue
            yes_settlement_value_dollars = item.get("yes_settlement_value_dollars")
            if yes_settlement_value_dollars is not None and not isinstance(
                yes_settlement_value_dollars, str
            ):
                LOGGER.warning(
                    "Ignoring unexpected yes_settlement_value_dollars type in markets[%s] at index %s: %s",
                    index,
                    leg_index,
                    self._describe_value(yes_settlement_value_dollars),
                )
                yes_settlement_value_dollars = None
            parsed.append(
                MveSelectedLeg(
                    event_ticker=event_ticker,
                    market_ticker=market_ticker,
                    side=side,
                    yes_settlement_value_dollars=yes_settlement_value_dollars,
                )
            )
        return parsed

    def _parse_settlement_sources(
        self, raw_settlement_sources: Any, index: int
    ) -> list[SettlementSource] | None:
        if not isinstance(raw_settlement_sources, list):
            LOGGER.warning(
                "Skipping series[%s]: expected 'settlement_sources' as object array, got %s",
                index,
                self._describe_value(raw_settlement_sources),
            )
            return None

        parsed_sources: list[SettlementSource] = []
        for source_index, raw_source in enumerate(raw_settlement_sources):
            if not isinstance(raw_source, dict):
                LOGGER.warning(
                    "Skipping invalid settlement source in series[%s] at index %s: %s",
                    index,
                    source_index,
                    self._describe_value(raw_source),
                )
                continue

            name = raw_source.get("name")
            url = raw_source.get("url")
            if not isinstance(name, str) or not isinstance(url, str):
                LOGGER.warning(
                    "Skipping invalid settlement source in series[%s] at index %s: name=%s url=%s",
                    index,
                    source_index,
                    self._describe_value(name),
                    self._describe_value(url),
                )
                continue

            parsed_sources.append(SettlementSource(name=name, url=url))

        return parsed_sources

    def _describe_value(self, value: Any) -> str:
        preview = repr(value)
        if len(preview) > 120:
            preview = f"{preview[:117]}..."
        return f"type={type(value).__name__} value={preview}"

    def _require_int_field(self, payload: dict[str, Any], field: str, *, endpoint: str) -> int:
        value = payload.get(field)
        if isinstance(value, bool) or not isinstance(value, int):
            LOGGER.error(
                "Unexpected %s payload: expected integer at '%s', got=%s keys=%s",
                endpoint,
                field,
                self._describe_value(value),
                sorted(payload.keys()),
            )
            raise KalshiClientError(
                f"Unexpected response shape from Kalshi API: missing integer '{field}'."
            )
        return value

    def _require_auth_headers(self, method: str, path: str) -> dict[str, str]:
        if not self._api_key_id or not (self._api_key_path or self._api_key_pem):
            raise KalshiClientError(
                "Authenticated Kalshi endpoint requires KALSHI_API_KEY_ID and "
                "KALSHI_API_KEY_PATH."
            )

        timestamp_ms = str(int(time.time() * 1000))
        message = f"{timestamp_ms}{method.upper()}{self._path_for_signing(path)}"
        signature = self._sign_message(message)

        return {
            "KALSHI-ACCESS-KEY": self._api_key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        }

    def _path_for_signing(self, path: str) -> str:
        request_path = path if path.startswith("/") else f"/{path}"
        request_path = request_path.split("?", 1)[0]

        parsed_base = parse.urlparse(self._base_url)
        base_path = parsed_base.path.rstrip("/")
        if base_path:
            return f"{base_path}{request_path}"
        return request_path

    def _sign_message(self, message: str) -> str:
        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import padding
        except Exception as exc:
            raise KalshiClientError(
                "Kalshi authenticated endpoints require the 'cryptography' package."
            ) from exc

        if self._cached_private_key is None:
            if self._api_key_pem:
                key_bytes = self._api_key_pem.encode("utf-8")
            else:
                try:
                    with open(self._api_key_path, "rb") as key_file:
                        key_bytes = key_file.read()
                except OSError as exc:
                    raise KalshiClientError(
                        f"Unable to read API key file at {self._api_key_path}: {exc}"
                    ) from exc

            try:
                if key_bytes.lstrip().startswith(b"-----"):
                    self._cached_private_key = serialization.load_pem_private_key(
                        key_bytes,
                        password=None,
                    )
                else:
                    self._cached_private_key = serialization.load_der_private_key(
                        base64.b64decode(key_bytes),
                        password=None,
                    )
            except Exception as exc:
                raise KalshiClientError("Unable to load the Kalshi private key.") from exc

        try:
            signature = self._cached_private_key.sign(
                message.encode("utf-8"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH,
                ),
                hashes.SHA256(),
            )
        except Exception as exc:
            raise KalshiClientError("Unable to sign Kalshi API request.") from exc

        return base64.b64encode(signature).decode("ascii")

    def search_events(self, query: str, page_size: int) -> list[dict[str, Any]]:
        """Kalshi's site search: events matching text, each with its markets and prices."""
        root = self._base_url.split("/trade-api/", 1)[0]
        params = parse.urlencode({"query": query, "order_by": "querymatch", "page_size": page_size})
        payload = self._get_json("", url=f"{root}/v1/search/series?{params}")
        results = payload.get("current_page")
        return [r for r in results if isinstance(r, dict)] if isinstance(results, list) else []

    def _get_json(self, path: str, *, authenticated: bool = False, url: str | None = None) -> dict[str, Any]:
        url = url or f"{self._base_url}{path}"
        headers = {"Accept": "application/json"}
        if authenticated:
            headers.update(self._require_auth_headers("GET", path))
        req = request.Request(
            url=url,
            method="GET",
            headers=headers,
        )
        attempts = 0
        max_attempts = 4
        while True:
            try:
                with request.urlopen(req, timeout=self._timeout_seconds) as response:
                    body = response.read().decode("utf-8")
                break
            except error.HTTPError as exc:
                attempts += 1
                retriable = exc.code in (429, 500, 502, 503, 504)
                if retriable and attempts < max_attempts:
                    retry_after = None
                    try:
                        retry_after = exc.headers.get("Retry-After")
                    except Exception:
                        retry_after = None

                    backoff = 0.25 * (2 ** (attempts - 1)) + random.uniform(0, 0.25)
                    if retry_after:
                        try:
                            backoff = max(backoff, float(retry_after))
                        except ValueError:
                            pass
                    backoff = min(backoff, 5.0)

                    LOGGER.warning(
                        "Kalshi API HTTP %s for %s; retrying in %.2fs (attempt %s/%s)",
                        exc.code,
                        url,
                        backoff,
                        attempts,
                        max_attempts,
                    )
                    time.sleep(backoff)
                    continue

                raise KalshiClientError(f"Kalshi API HTTP {exc.code} for {url}", exc.code) from exc
            except error.URLError as exc:
                attempts += 1
                if attempts < max_attempts:
                    backoff = min(0.25 * (2 ** (attempts - 1)) + random.uniform(0, 0.25), 2.0)
                    LOGGER.warning(
                        "Kalshi API request failed for %s: %s; retrying in %.2fs (attempt %s/%s)",
                        url,
                        exc.reason,
                        backoff,
                        attempts,
                        max_attempts,
                    )
                    time.sleep(backoff)
                    continue
                raise KalshiClientError(f"Kalshi API request failed for {url}: {exc.reason}") from exc

        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as exc:
            raise KalshiClientError(f"Kalshi API response was not valid JSON for {url}") from exc

        if not isinstance(decoded, dict):
            raise KalshiClientError(f"Kalshi API returned a non-object payload for {url}")

        return decoded

