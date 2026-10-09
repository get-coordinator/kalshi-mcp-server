import unittest

from kalshi_mcp.mcp.handlers import (
    handle_get_balance,
    handle_get_order,
    handle_get_orders,
    handle_get_positions,
    handle_get_series_list,
    handle_get_series_tickers_for_category,
    handle_get_categories,
    handle_get_subaccount_balances,
    handle_get_tags_for_series_categories,
    handle_get_tags_for_series_category,
    handle_get_markets,
    handle_get_open_markets_for_series,
    handle_get_open_market_titles_for_series,
)
from kalshi_mcp.models import (
    EventPosition,
    Market,
    MarketPosition,
    MarketsList,
    PortfolioBalance,
    PortfolioOrder,
    PortfolioOrdersList,
    PortfolioPositions,
    Series,
    SeriesList,
    SettlementSource,
    SubaccountBalance,
    SubaccountBalancesList,
    TagsByCategories,
)


class _FakeMetadataService:
    def get_tags_for_series_categories(self) -> TagsByCategories:
        return TagsByCategories(
            tags_by_categories={
                "Politics": ["Trump", "Biden"],
                "Crypto": ["BTC", "ETH"],
            }
        )

    def get_categories(self) -> list[str]:
        return ["Crypto", "Politics"]

    def get_tags_for_series_category(self, category: str) -> list[str]:
        if category == "Crypto":
            return ["BTC", "ETH"]
        raise ValueError(f"Unknown category: {category}")

    def get_series_list(
        self,
        category: str | None = None,
        tags: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
        include_product_metadata: bool = False,
        include_volume: bool = False,
    ) -> SeriesList:
        _ = include_product_metadata
        _ = include_volume
        _ = cursor
        _ = limit
        if category == "Crypto" and tags == "BTC":
            return SeriesList(
                series=[
                    Series(
                        ticker="KXBTCUSD",
                        frequency="daily",
                        title="Will Bitcoin close above 100k?",
                        category="Crypto",
                        tags=["BTC"],
                        settlement_sources=[
                            SettlementSource(
                                name="Kalshi Rules", url="https://kalshi.com/rules"
                            )
                        ],
                        contract_url="https://kalshi.com/series/KXBTCUSD",
                        contract_terms_url="https://kalshi.com/terms/KXBTCUSD",
                        fee_type="linear",
                        fee_multiplier=1.0,
                        additional_prohibitions=[],
                    )
                ],
                cursor="next-page",
            )
        if category == "Crypto" and tags is None:
            if cursor is None:
                return SeriesList(
                    series=[
                        Series(
                            ticker="KXBTCUSD",
                            frequency="daily",
                            title="Will Bitcoin close above 100k?",
                            category="Crypto",
                            tags=["BTC"],
                            settlement_sources=[
                                SettlementSource(
                                    name="Kalshi Rules", url="https://kalshi.com/rules"
                                )
                            ],
                            contract_url="https://kalshi.com/series/KXBTCUSD",
                            contract_terms_url="https://kalshi.com/terms/KXBTCUSD",
                            fee_type="linear",
                            fee_multiplier=1.0,
                            additional_prohibitions=[],
                        )
                    ],
                    cursor="page-2",
                )
            if cursor == "page-2":
                return SeriesList(
                    series=[
                        Series(
                            ticker="KXETHUSD",
                            frequency="daily",
                            title="Will Ethereum close above 10k?",
                            category="Crypto",
                            tags=["ETH"],
                            settlement_sources=[
                                SettlementSource(
                                    name="Kalshi Rules", url="https://kalshi.com/rules"
                                )
                            ],
                            contract_url="https://kalshi.com/series/KXETHUSD",
                            contract_terms_url="https://kalshi.com/terms/KXETHUSD",
                            fee_type="linear",
                            fee_multiplier=1.0,
                            additional_prohibitions=[],
                        )
                    ],
                    cursor=None,
                )
        return SeriesList(series=[], cursor=None)

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
        _ = (
            cursor,
            limit,
            event_ticker,
            series_ticker,
            tickers,
            status,
            mve_filter,
            min_created_ts,
            max_created_ts,
            min_updated_ts,
            min_close_ts,
            max_close_ts,
            min_settled_ts,
            max_settled_ts,
        )
        return MarketsList(
            markets=[
                Market(
                    ticker="TRUMPWIN-26NOV-T2",
                    event_ticker="TRUMPWIN-26NOV",
                    market_type="binary",
                    title="Will Trump win the 2024 election?",
                    subtitle="Trump Wins",
                    status="initialized",
                    tick_size=1,
                )
            ],
            cursor="next-page",
        )


class _FakePortfolioService:
    def get_balance(self) -> PortfolioBalance:
        return PortfolioBalance(
            balance=12345,
            portfolio_value=23456,
            updated_ts=1731000000000,
        )

    def get_subaccount_balances(self) -> SubaccountBalancesList:
        return SubaccountBalancesList(
            subaccount_balances=[
                SubaccountBalance(
                    subaccount_number=1,
                    balance="100.50",
                    updated_ts=1731000000000,
                ),
                SubaccountBalance(
                    subaccount_number=2,
                    balance="200.75",
                    updated_ts=1731000001000,
                ),
            ]
        )

    def get_order(self, order_id: str) -> PortfolioOrder:
        return PortfolioOrder(
            order_id=order_id,
            user_id="user-1",
            client_order_id="client-1",
            ticker="KXBTCUSD-26JAN01-T1",
            status="resting",
            side="yes",
            action="buy",
            type="limit",
            yes_price=55,
            no_price=45,
            fill_count=0,
            remaining_count=10,
            initial_count=10,
            taker_fees=0,
            maker_fees=0,
            taker_fill_cost=0,
            maker_fill_cost=0,
            queue_position=1,
            yes_price_dollars="0.55",
            no_price_dollars="0.45",
            fill_count_fp="0.0000",
            remaining_count_fp="10.0000",
            initial_count_fp="10.0000",
            taker_fill_cost_dollars="0.00",
            maker_fill_cost_dollars="0.00",
            subaccount_number=0,
        )

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
        _ = (cursor, limit, count_filter, ticker, event_ticker, subaccount)
        return PortfolioPositions(
            cursor="next-pos-cursor",
            market_positions=[
                MarketPosition(
                    ticker="KXBTCUSD-26JAN01-T1",
                    total_traded=100,
                    total_traded_dollars="100.00",
                    position=10,
                    position_fp="10.0000",
                    market_exposure=50,
                    market_exposure_dollars="50.00",
                    realized_pnl=5,
                    realized_pnl_dollars="5.00",
                    resting_orders_count=2,
                    fees_paid=1,
                    fees_paid_dollars="1.00",
                    last_updated_ts="1731000000000",
                ),
            ],
            event_positions=[
                EventPosition(
                    event_ticker="KXBTCUSD-26JAN01",
                    total_cost=200,
                    total_cost_dollars="200.00",
                    total_cost_shares=20,
                    total_cost_shares_fp="20.0000",
                    event_exposure=100,
                    event_exposure_dollars="100.00",
                    realized_pnl=10,
                    realized_pnl_dollars="10.00",
                    fees_paid=2,
                    fees_paid_dollars="2.00",
                    resting_orders_count=1,
                ),
            ],
        )

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
        _ = (ticker, event_ticker, min_ts, max_ts, status, limit, cursor, subaccount)
        return PortfolioOrdersList(
            orders=[
                PortfolioOrder(
                    order_id="order-1",
                    user_id="user-1",
                    client_order_id="client-1",
                    ticker="KXBTCUSD-26JAN01-T1",
                    status="resting",
                    side="yes",
                    action="buy",
                    type="limit",
                    yes_price=55,
                    no_price=45,
                    fill_count=0,
                    remaining_count=10,
                    initial_count=10,
                    taker_fees=0,
                    maker_fees=0,
                    taker_fill_cost=0,
                    maker_fill_cost=0,
                    queue_position=1,
                    yes_price_dollars="0.55",
                    no_price_dollars="0.45",
                    fill_count_fp="0.0000",
                    remaining_count_fp="10.0000",
                    initial_count_fp="10.0000",
                    taker_fill_cost_dollars="0.00",
                    maker_fill_cost_dollars="0.00",
                    subaccount_number=0,
                )
            ],
            cursor="next-cursor",
        )


class _CaptureOrdersPortfolioService(_FakePortfolioService):
    def __init__(self) -> None:
        self.last_get_orders_args: dict[str, int | str | None] | None = None

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
        self.last_get_orders_args = {
            "ticker": ticker,
            "event_ticker": event_ticker,
            "min_ts": min_ts,
            "max_ts": max_ts,
            "status": status,
            "limit": limit,
            "cursor": cursor,
            "subaccount": subaccount,
        }
        return super().get_orders(
            ticker=ticker,
            event_ticker=event_ticker,
            min_ts=min_ts,
            max_ts=max_ts,
            status=status,
            limit=limit,
            cursor=cursor,
            subaccount=subaccount,
        )


class _PagingMarketsMetadataService(_FakeMetadataService):
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
        _ = (
            limit,
            event_ticker,
            tickers,
            mve_filter,
            min_created_ts,
            max_created_ts,
            min_updated_ts,
            min_close_ts,
            max_close_ts,
            min_settled_ts,
            max_settled_ts,
        )

        # Simulate a 2-page /markets response for series KXBTCUSD.
        if series_ticker == "KXBTCUSD" and status == "open":
            if cursor is None:
                return MarketsList(
                    markets=[
                        Market(
                            ticker="KXBTCUSD-25JAN01-T1",
                            event_ticker="KXBTCUSD-25JAN01",
                            market_type="binary",
                            title="Will Bitcoin close above 100k on Jan 1?",
                            subtitle="Yes",
                            status="open",
                            series_ticker="KXBTCUSD",
                        )
                    ],
                    cursor="page-2",
                )
            if cursor == "page-2":
                return MarketsList(
                    markets=[
                        Market(
                            ticker="KXBTCUSD-25JAN02-T1",
                            event_ticker="KXBTCUSD-25JAN02",
                            market_type="binary",
                            title="Will Bitcoin close above 100k on Jan 2?",
                            subtitle="Yes",
                            status="open",
                            series_ticker="KXBTCUSD",
                        )
                    ],
                    cursor=None,
                )

        return MarketsList(markets=[], cursor=None)

class HandlersTests(unittest.TestCase):
    def test_get_tags_for_series_categories_handler(self) -> None:
        result = handle_get_tags_for_series_categories(_FakeMetadataService(), None)
        self.assertEqual(
            result,
            {"tags_by_categories": {"Politics": ["Trump", "Biden"], "Crypto": ["BTC", "ETH"]}},
        )

    def test_get_tags_for_series_categories_rejects_arguments(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_tags_for_series_categories(_FakeMetadataService(), {"unexpected": True})

    def test_get_balance_handler(self) -> None:
        result = handle_get_balance(_FakePortfolioService(), None)
        self.assertEqual(
            {
                "balance": 12345,
                "portfolio_value": 23456,
                "updated_ts": 1731000000000,
            },
            result,
        )

    def test_get_balance_rejects_arguments(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_balance(_FakePortfolioService(), {"unexpected": True})

    def test_get_subaccount_balances_handler(self) -> None:
        result = handle_get_subaccount_balances(_FakePortfolioService(), None)
        self.assertEqual(
            {
                "subaccount_balances": [
                    {
                        "subaccount_number": 1,
                        "balance": "100.50",
                        "updated_ts": 1731000000000,
                    },
                    {
                        "subaccount_number": 2,
                        "balance": "200.75",
                        "updated_ts": 1731000001000,
                    },
                ],
            },
            result,
        )

    def test_get_subaccount_balances_rejects_arguments(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_subaccount_balances(_FakePortfolioService(), {"unexpected": True})

    def test_get_categories_handler(self) -> None:
        result = handle_get_categories(_FakeMetadataService(), None)
        self.assertEqual({"categories": ["Crypto", "Politics"]}, result)

    def test_get_categories_rejects_arguments(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_categories(_FakeMetadataService(), {"unexpected": True})

    def test_get_tags_for_series_category_handler(self) -> None:
        result = handle_get_tags_for_series_category(
            _FakeMetadataService(), {"category": "Crypto"}
        )
        self.assertEqual({"category": "Crypto", "tags": ["BTC", "ETH"]}, result)

    def test_get_tags_for_series_category_requires_arguments(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_tags_for_series_category(_FakeMetadataService(), None)

    def test_get_tags_for_series_category_requires_string_category(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_tags_for_series_category(_FakeMetadataService(), {"category": 123})

    def test_get_series_list_handler(self) -> None:
        result = handle_get_series_list(
            _FakeMetadataService(),
            {
                "category": "Crypto",
                "tags": "BTC",
                "include_product_metadata": True,
                "include_volume": True,
            },
        )
        self.assertEqual(1, len(result["series"]))
        self.assertEqual("KXBTCUSD", result["series"][0]["ticker"])
        self.assertEqual("next-page", result["cursor"])

    def test_get_series_list_rejects_invalid_types(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_series_list(_FakeMetadataService(), {"include_volume": "yes"})

    def test_get_series_list_rejects_invalid_limit(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_series_list(_FakeMetadataService(), {"limit": 0})

    def test_get_series_tickers_for_category_handler(self) -> None:
        result = handle_get_series_tickers_for_category(
            _FakeMetadataService(),
            {"category": "Crypto"},
        )
        self.assertEqual(
            {
                "category": "Crypto",
                "tickers": ["KXBTCUSD", "KXETHUSD"],
                "count": 2,
                "pages": 2,
            },
            result,
        )

    def test_get_series_tickers_for_category_requires_arguments(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_series_tickers_for_category(_FakeMetadataService(), None)

    def test_get_series_tickers_for_category_requires_string_category(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_series_tickers_for_category(_FakeMetadataService(), {"category": 123})

    def test_get_markets_handler(self) -> None:
        result = handle_get_markets(_FakeMetadataService(), {"limit": 1, "status": "open"})
        self.assertEqual(1, len(result["markets"]))
        self.assertEqual("TRUMPWIN-26NOV-T2", result["markets"][0]["ticker"])
        self.assertEqual("initialized", result["markets"][0]["status"])
        self.assertEqual("next-page", result["cursor"])

    def test_get_markets_rejects_invalid_limit(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_markets(_FakeMetadataService(), {"limit": 0})

    def test_get_markets_rejects_invalid_mve_filter(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_markets(_FakeMetadataService(), {"mve_filter": "maybe"})

    def test_get_open_markets_for_series_pages_and_forces_open(self) -> None:
        result = handle_get_open_markets_for_series(
            _PagingMarketsMetadataService(), {"series_ticker": "KXBTCUSD"}
        )
        self.assertEqual("KXBTCUSD", result["series_ticker"])
        self.assertEqual("open", result["status"])
        self.assertEqual(2, result["count"])
        self.assertEqual(2, result["pages"])
        self.assertEqual(["KXBTCUSD-25JAN01-T1", "KXBTCUSD-25JAN02-T1"], [m["ticker"] for m in result["markets"]])

    def test_get_open_market_titles_for_series_returns_only_title_fields(self) -> None:
        result = handle_get_open_market_titles_for_series(
            _PagingMarketsMetadataService(), {"series_ticker": "KXBTCUSD"}
        )
        self.assertEqual("KXBTCUSD", result["series_ticker"])
        self.assertEqual("open", result["status"])
        self.assertEqual(2, result["count"])
        self.assertEqual(2, result["pages"])
        first = result["markets"][0]
        self.assertEqual(
            {"ticker", "title", "subtitle", "yes_sub_title", "no_sub_title"}, set(first.keys())
        )

    def test_get_open_markets_for_series_requires_arguments(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_open_markets_for_series(_FakeMetadataService(), None)

    def test_get_open_market_titles_for_series_requires_arguments(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_open_market_titles_for_series(_FakeMetadataService(), None)

    def test_get_orders_handler(self) -> None:
        result = handle_get_orders(
            _FakePortfolioService(),
            {
                "ticker": "KXBTCUSD-26JAN01-T1",
                "event_ticker": "KXBTCUSD-26JAN01",
                "min_ts": 1700000000,
                "max_ts": 1700001000,
                "status": "resting",
                "limit": 50,
                "cursor": "c1",
                "subaccount": 0,
            },
        )
        self.assertEqual(1, len(result["orders"]))
        self.assertEqual("order-1", result["orders"][0]["order_id"])
        self.assertEqual("next-cursor", result["cursor"])

    def test_get_orders_defaults_to_optional_filters(self) -> None:
        service = _CaptureOrdersPortfolioService()
        result = handle_get_orders(service, None)
        self.assertEqual(1, len(result["orders"]))
        self.assertEqual(
            {
                "ticker": None,
                "event_ticker": None,
                "min_ts": None,
                "max_ts": None,
                "status": None,
                "limit": None,
                "cursor": None,
                "subaccount": None,
            },
            service.last_get_orders_args,
        )

    def test_get_orders_rejects_invalid_status(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_orders(_FakePortfolioService(), {"status": "open"})

    def test_get_orders_rejects_invalid_limit(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_orders(_FakePortfolioService(), {"limit": 201})

    def test_get_orders_rejects_invalid_subaccount(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_orders(_FakePortfolioService(), {"subaccount": 33})

    def test_get_order_handler(self) -> None:
        result = handle_get_order(
            _FakePortfolioService(),
            {"order_id": "order-abc-123"},
        )
        self.assertEqual("order-abc-123", result["order_id"])
        self.assertEqual("user-1", result["user_id"])
        self.assertEqual("KXBTCUSD-26JAN01-T1", result["ticker"])
        self.assertEqual("resting", result["status"])
        self.assertEqual("yes", result["side"])
        self.assertEqual("buy", result["action"])
        self.assertEqual(0, result["subaccount_number"])

    def test_get_order_requires_arguments(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_order(_FakePortfolioService(), None)

    def test_get_order_rejects_empty_order_id(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_order(_FakePortfolioService(), {"order_id": ""})

    def test_get_order_rejects_non_string_order_id(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_order(_FakePortfolioService(), {"order_id": 123})

    def test_handle_get_positions(self) -> None:
        result = handle_get_positions(_FakePortfolioService(), None)
        self.assertEqual(1, len(result["market_positions"]))
        self.assertEqual("KXBTCUSD-26JAN01-T1", result["market_positions"][0]["ticker"])
        self.assertEqual(10, result["market_positions"][0]["position"])
        self.assertEqual("10.0000", result["market_positions"][0]["position_fp"])
        self.assertEqual(50, result["market_positions"][0]["market_exposure"])
        self.assertEqual("50.00", result["market_positions"][0]["market_exposure_dollars"])
        self.assertEqual(5, result["market_positions"][0]["realized_pnl"])
        self.assertEqual(2, result["market_positions"][0]["resting_orders_count"])
        self.assertEqual(1, result["market_positions"][0]["fees_paid"])
        self.assertEqual("1731000000000", result["market_positions"][0]["last_updated_ts"])

        self.assertEqual(1, len(result["event_positions"]))
        self.assertEqual("KXBTCUSD-26JAN01", result["event_positions"][0]["event_ticker"])
        self.assertEqual(200, result["event_positions"][0]["total_cost"])
        self.assertEqual("200.00", result["event_positions"][0]["total_cost_dollars"])
        self.assertEqual(20, result["event_positions"][0]["total_cost_shares"])
        self.assertEqual(100, result["event_positions"][0]["event_exposure"])
        self.assertEqual(10, result["event_positions"][0]["realized_pnl"])
        self.assertEqual(1, result["event_positions"][0]["resting_orders_count"])

        self.assertEqual("next-pos-cursor", result["cursor"])

    def test_handle_get_positions_with_filters(self) -> None:
        result = handle_get_positions(
            _FakePortfolioService(),
            {
                "cursor": "c1",
                "limit": 100,
                "count_filter": "position,total_traded",
                "ticker": "KXBTCUSD-26JAN01-T1",
                "event_ticker": "KXBTCUSD-26JAN01",
                "subaccount": 0,
            },
        )
        self.assertEqual(1, len(result["market_positions"]))
        self.assertEqual(1, len(result["event_positions"]))

    def test_handle_get_positions_rejects_invalid_count_filter(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_positions(_FakePortfolioService(), {"count_filter": "invalid"})

    def test_handle_get_positions_rejects_invalid_count_filter_csv(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_positions(
                _FakePortfolioService(),
                {"count_filter": "position,invalid"},
            )

    def test_handle_get_positions_rejects_invalid_limit(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_positions(_FakePortfolioService(), {"limit": 0})

    def test_handle_get_positions_rejects_invalid_subaccount(self) -> None:
        with self.assertRaises(ValueError):
            handle_get_positions(_FakePortfolioService(), {"subaccount": 33})


if __name__ == "__main__":
    unittest.main()
