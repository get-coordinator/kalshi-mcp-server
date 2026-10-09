"""Application-level use cases."""

from .kalshi_client import KalshiClient
from .models import (
    MarketsList,
    PortfolioBalance,
    PortfolioOrder,
    PortfolioOrdersList,
    PortfolioPositions,
    SeriesList,
    SubaccountBalancesList,
    TagsByCategories,
)


class MetadataService:
    def __init__(self, client: KalshiClient) -> None:
        self._client = client

    def get_tags_for_series_categories(self) -> TagsByCategories:
        return self._client.get_tags_for_series_categories()

    def get_categories(self) -> list[str]:
        tags_by_categories = self.get_tags_for_series_categories().tags_by_categories
        return sorted(tags_by_categories.keys())

    def get_tags_for_series_category(self, category: str) -> list[str]:
        normalized_category = category.strip()
        if not normalized_category:
            raise ValueError("category must be a non-empty string.")

        tags_by_categories = self.get_tags_for_series_categories().tags_by_categories
        if normalized_category not in tags_by_categories:
            raise ValueError(f"Unknown category: {normalized_category}")

        return tags_by_categories[normalized_category]

    def get_series_list(
        self,
        category: str | None = None,
        tags: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
        include_product_metadata: bool = False,
        include_volume: bool = False,
    ) -> SeriesList:
        return self._client.get_series_list(
            category=category,
            tags=tags,
            cursor=cursor,
            limit=limit,
            include_product_metadata=include_product_metadata,
            include_volume=include_volume,
        )

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
        return self._client.get_markets(
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


class PortfolioService:
    def __init__(self, client: KalshiClient) -> None:
        self._client = client

    def get_balance(self) -> PortfolioBalance:
        return self._client.get_balance()

    def get_subaccount_balances(self) -> SubaccountBalancesList:
        return self._client.get_subaccount_balances()

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
        return self._client.get_orders(
            ticker=ticker,
            event_ticker=event_ticker,
            min_ts=min_ts,
            max_ts=max_ts,
            status=status,
            limit=limit,
            cursor=cursor,
            subaccount=subaccount,
        )

    def get_order(self, order_id: str) -> PortfolioOrder:
        return self._client.get_order(order_id)

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
        return self._client.get_positions(
            cursor=cursor,
            limit=limit,
            count_filter=count_filter,
            ticker=ticker,
            event_ticker=event_ticker,
            subaccount=subaccount,
        )
