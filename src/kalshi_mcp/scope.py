"""Limits every tool to the Kalshi categories COORDINATOR covers.

Categories, tags and series outside them are never listed, markets, orders and
positions outside them are dropped from results, and asking for one by name is
refused. A market belongs to the series whose ticker is the longest prefix of
its own ("KXNFLWINS-BUF-26-T10" is in series "KXNFLWINS-BUF").
"""

from __future__ import annotations

import threading
import time
from typing import Any

ALLOWED_CATEGORIES = (
    "Sports",
    "Economics",
    "Crypto",
    "Science and Technology",
    "Financials",
    "Politics",
    "Elections",
)

OUT_OF_SCOPE = (
    "COORDINATOR only covers Kalshi's sports, economics, crypto, tech, finance "
    "and politics markets."
)

UNKNOWN_SERIES = (
    "{ticker} isn't a Kalshi series COORDINATOR covers. Find the market with "
    "search_markets (e.g. the teams or the topic) and use the tickers it returns."
)

SERIES_TTL_SECONDS = 3600

_series_lock = threading.Lock()
_series_cache: dict[str, Any] = {"tickers": frozenset(), "expires": 0.0}


def in_series(ticker: str, series: frozenset[str]) -> bool:
    parts = ticker.split("-")
    return any("-".join(parts[: i + 1]) in series for i in range(len(parts)))


class CategoryScope:
    def __init__(self, registry: Any) -> None:
        self._registry = registry

    def list_tools(self) -> list[dict[str, Any]]:
        return self._registry.list_tools()

    def _series(self) -> frozenset[str]:
        with _series_lock:
            if _series_cache["expires"] > time.monotonic():
                return _series_cache["tickers"]
            tickers: set[str] = set()
            for category in ALLOWED_CATEGORIES:
                result = self._registry.call_tool("get_series_tickers_for_category", {"category": category})
                tickers.update(result.get("tickers") or [])
            _series_cache["tickers"] = frozenset(tickers)
            _series_cache["expires"] = time.monotonic() + SERIES_TTL_SECONDS
            return _series_cache["tickers"]

    def _allowed(self, ticker: Any) -> bool:
        return isinstance(ticker, str) and in_series(ticker, self._series())

    def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}

        category = args.get("category")
        if category is not None and category not in ALLOWED_CATEGORIES:
            raise ValueError(OUT_OF_SCOPE)
        series_ticker = args.get("series_ticker")
        if series_ticker is not None and not self._allowed(series_ticker):
            raise ValueError(UNKNOWN_SERIES.format(ticker=series_ticker))

        if tool_name == "get_markets" and "mve_filter" not in args:
            # Combo markets span categories; without this a page is mostly them.
            arguments = {**args, "mve_filter": "exclude"}

        result = self._registry.call_tool(tool_name, arguments)

        if tool_name == "search_markets":
            limit = args.get("limit") or 5
            result["events"] = [e for e in result.get("events") or [] if e.get("category") in ALLOWED_CATEGORIES][:limit]
        elif tool_name == "get_categories":
            result["categories"] = [c for c in result.get("categories") or [] if c in ALLOWED_CATEGORIES]
        elif tool_name == "get_tags_for_series_categories":
            tags = result.get("tags_by_categories") or {}
            result["tags_by_categories"] = {k: v for k, v in tags.items() if k in ALLOWED_CATEGORIES}
        elif tool_name == "get_series_list":
            result["series"] = [s for s in result.get("series") or [] if s.get("category") in ALLOWED_CATEGORIES]
        elif tool_name in ("get_markets", "get_open_markets_for_series", "get_open_market_titles_for_series"):
            result["markets"] = [m for m in result.get("markets") or [] if self._allowed(m.get("ticker"))]
            if "count" in result:
                result["count"] = len(result["markets"])
        elif tool_name == "get_orders":
            result["orders"] = [o for o in result.get("orders") or [] if self._allowed(o.get("ticker"))]
        elif tool_name == "get_order":
            if not self._allowed(result.get("ticker")):
                raise ValueError(OUT_OF_SCOPE)
        elif tool_name == "get_positions":
            result["market_positions"] = [
                p for p in result.get("market_positions") or [] if self._allowed(p.get("ticker"))
            ]
            result["event_positions"] = [
                p for p in result.get("event_positions") or [] if self._allowed(p.get("event_ticker"))
            ]
        return result
