import unittest

from kalshi_mcp import scope
from kalshi_mcp.scope import OUT_OF_SCOPE, CategoryScope, in_series


class _Fake:
    def __init__(self) -> None:
        self.series = {"Sports": ["KXNFLGAME", "KXNFLWINS-BUF"], "Economics": ["KXFED"]}

    def list_tools(self):
        return []

    def call_tool(self, name, args=None):
        args = args or {}
        if name == "get_series_tickers_for_category":
            return {"category": args["category"], "tickers": self.series.get(args["category"], [])}
        if name == "get_categories":
            return {"categories": ["Sports", "Entertainment", "Economics", "Climate and Weather"]}
        if name == "get_tags_for_series_categories":
            return {"tags_by_categories": {"Sports": ["Football"], "Mentions": ["X"]}}
        if name == "get_series_list":
            return {"series": [{"ticker": "KXNFLGAME", "category": "Sports"}, {"ticker": "KXOSCARS", "category": "Entertainment"}]}
        if name in ("get_markets", "get_open_market_titles_for_series"):
            return {"markets": [{"ticker": "KXNFLGAME-26OCT19WASSF-WAS"}, {"ticker": "KXOSCARS-27-BP"}], "count": 2}
        if name == "get_positions":
            return {
                "market_positions": [{"ticker": "KXNFLWINS-BUF-26-T10"}, {"ticker": "KXOSCARS-27-BP"}],
                "event_positions": [{"event_ticker": "KXFED-26DEC"}, {"event_ticker": "KXOSCARS-27"}],
            }
        if name == "get_order":
            return {"order_id": args["order_id"], "ticker": "KXOSCARS-27-BP"}
        if name == "get_balance":
            return {"balance": 100}
        if name == "search_markets":
            return {"events": [
                {"event_ticker": "KXOSCARS-27", "category": "Entertainment"},
                {"event_ticker": "KXNFLGAME-26OCT19WASSF", "category": "Sports"},
                {"event_ticker": "KXFED-26OCT", "category": "Economics"},
            ]}
        raise AssertionError(name)


class CategoryScopeTest(unittest.TestCase):
    def setUp(self) -> None:
        scope._series_cache.update(tickers=frozenset(), expires=0.0)
        self.scope = CategoryScope(_Fake())

    def test_lists_only_allowed_categories(self) -> None:
        self.assertEqual(self.scope.call_tool("get_categories")["categories"], ["Sports", "Economics"])
        self.assertEqual(list(self.scope.call_tool("get_tags_for_series_categories")["tags_by_categories"]), ["Sports"])
        self.assertEqual([s["ticker"] for s in self.scope.call_tool("get_series_list")["series"]], ["KXNFLGAME"])

    def test_refuses_other_categories_and_series(self) -> None:
        for name, args in (
            ("get_tags_for_series_category", {"category": "Entertainment"}),
            ("get_series_list", {"category": "Climate and Weather"}),
            ("get_open_market_titles_for_series", {"series_ticker": "KXOSCARS"}),
            ("get_order", {"order_id": "o1"}),
        ):
            with self.assertRaisesRegex(ValueError, OUT_OF_SCOPE):
                self.scope.call_tool(name, args)

    def test_drops_markets_and_positions_outside(self) -> None:
        markets = self.scope.call_tool("get_markets", {})
        self.assertEqual([m["ticker"] for m in markets["markets"]], ["KXNFLGAME-26OCT19WASSF-WAS"])
        self.assertEqual(markets["count"], 1)
        positions = self.scope.call_tool("get_positions", {})
        self.assertEqual([p["ticker"] for p in positions["market_positions"]], ["KXNFLWINS-BUF-26-T10"])
        self.assertEqual([p["event_ticker"] for p in positions["event_positions"]], ["KXFED-26DEC"])

    def test_search_keeps_allowed_categories(self) -> None:
        got = self.scope.call_tool("search_markets", {"query": "x", "limit": 1})
        self.assertEqual([e["event_ticker"] for e in got["events"]], ["KXNFLGAME-26OCT19WASSF"])

    def test_balance_is_the_whole_account(self) -> None:
        self.assertEqual(self.scope.call_tool("get_balance")["balance"], 100)

    def test_series_by_longest_prefix(self) -> None:
        series = frozenset({"KXNFLWINS-BUF", "KXFED"})
        self.assertTrue(in_series("KXNFLWINS-BUF-26-T10", series))
        self.assertTrue(in_series("KXFED", series))
        self.assertFalse(in_series("KXNFLWINS-26", series))
        self.assertFalse(in_series("KXFEDX-26", series))


if __name__ == "__main__":
    unittest.main()
