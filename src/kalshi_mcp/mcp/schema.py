"""MCP tool schemas and I/O models."""

SEARCH_MARKETS_TOOL = {
    "name": "search_markets",
    "description": (
        "Find Kalshi prediction markets by text (a team, game, player, company, coin, person or topic) "
        "with each market's current odds: the yes price in dollars is the market's implied probability "
        "(0.77 = 77%). Start here for any question about Kalshi odds. Search with names (teams, people, "
        "companies, coins), not dates: each event's subtitle has its date to match. Covers sports, "
        "economics, crypto, tech, finance and politics."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to look for, e.g. \"Commanders 49ers\" or \"Fed October\"."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Events to return (default 5)."},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}

GET_TAGS_FOR_SERIES_CATEGORIES_TOOL = {
    "name": "get_tags_for_series_categories",
    "description": (
        "Kalshi's sub-topics (tags like Football, Basketball, Fed, Bitcoin) for every category COORDINATOR covers (sports, economics, crypto, tech, finance and politics)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}

GET_BALANCE_TOOL = {
    "name": "get_balance",
    "description": (
        "The user's own Kalshi cash balance and portfolio value (needs their read-only API key)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}

GET_CATEGORIES_TOOL = {
    "name": "get_categories",
    "description": (
        "The Kalshi prediction market categories COORDINATOR covers: sports, economics, crypto, tech, finance and politics."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}

GET_TAGS_FOR_SERIES_CATEGORY_TOOL = {
    "name": "get_tags_for_series_category",
    "description": (
        "Kalshi's sub-topics (tags) within one category, e.g. Football or Basketball in Sports."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Exact Kalshi series category name.",
                "minLength": 1,
            }
        },
        "required": ["category"],
        "additionalProperties": False,
    },
}

GET_SERIES_LIST_TOOL = {
    "name": "get_series_list",
    "description": (
        "Kalshi market series: recurring families of prediction markets such as NFL games (KXNFLGAME) or Fed decisions, filterable by category and tag. Use a series ticker with the market tools."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Optional category filter.",
                "minLength": 1,
            },
            "tags": {
                "type": "string",
                "description": "Optional tags filter.",
                "minLength": 1,
            },
            "cursor": {
                "type": "string",
                "description": "Optional pagination cursor.",
                "minLength": 1,
            },
            "limit": {
                "type": "integer",
                "description": "Optional page size (1-1000).",
                "minimum": 1,
                "maximum": 1000,
            },
            "include_product_metadata": {
                "type": "boolean",
                "description": "Include product metadata in each series item.",
            },
            "include_volume": {
                "type": "boolean",
                "description": "Include volume fields in each series item.",
            },
        },
        "additionalProperties": False,
    },
}

GET_MARKETS_TOOL = {
    "name": "get_markets",
    "description": (
        "Kalshi prediction markets with their current prices: yes bid/ask and last price in dollars are the market's implied probability (0.77 = 77%). Filter by series_ticker, event_ticker or tickers; search_markets is usually the better start."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "cursor": {
                "type": "string",
                "description": "Optional pagination cursor.",
                "minLength": 1,
            },
            "limit": {
                "type": "integer",
                "description": "Optional page size (1-1000).",
                "minimum": 1,
                "maximum": 1000,
            },
            "status": {
                "type": "string",
                "description": (
                    "Optional market status filter (Kalshi docs list values like "
                    "unopened, open, paused, closed, settled)."
                ),
                "minLength": 1,
            },
            "tickers": {
                "type": "string",
                "description": "Optional comma-separated list of market tickers to retrieve.",
                "minLength": 1,
            },
            "event_ticker": {
                "type": "string",
                "description": (
                    "Optional comma-separated list of event tickers to retrieve. "
                    "Kalshi docs note a maximum of 10."
                ),
                "minLength": 1,
            },
            "series_ticker": {
                "type": "string",
                "description": "Optional series ticker to filter markets by.",
                "minLength": 1,
            },
            "mve_filter": {
                "type": "string",
                "description": "Optional filter for multiple-vs-binary markets.",
                "enum": ["only", "exclude"],
            },
            "min_created_ts": {
                "type": "integer",
                "description": "Optional minimum unix timestamp (seconds) for market creation time.",
                "minimum": 0,
            },
            "max_created_ts": {
                "type": "integer",
                "description": "Optional maximum unix timestamp (seconds) for market creation time.",
                "minimum": 0,
            },
            "min_updated_ts": {
                "type": "integer",
                "description": "Optional minimum unix timestamp (seconds) for market update time.",
                "minimum": 0,
            },
            "min_close_ts": {
                "type": "integer",
                "description": "Optional minimum unix timestamp (seconds) for market close time.",
                "minimum": 0,
            },
            "max_close_ts": {
                "type": "integer",
                "description": "Optional maximum unix timestamp (seconds) for market close time.",
                "minimum": 0,
            },
            "min_settled_ts": {
                "type": "integer",
                "description": "Optional minimum unix timestamp (seconds) for market settlement time.",
                "minimum": 0,
            },
            "max_settled_ts": {
                "type": "integer",
                "description": "Optional maximum unix timestamp (seconds) for market settlement time.",
                "minimum": 0,
            },
        },
        "additionalProperties": False,
    },
}

GET_OPEN_MARKETS_FOR_SERIES_TOOL = {
    "name": "get_open_markets_for_series",
    "description": (
        "Every open Kalshi market in one series (e.g. KXNFLGAME for NFL games, KXFEDDECISION for Fed meetings) with current prices, the market's implied odds."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "series_ticker": {
                "type": "string",
                "description": "Series ticker to filter markets by.",
                "minLength": 1,
            },
            "limit": {
                "type": "integer",
                "description": "Optional page size for each /markets request (1-1000). Defaults to 1000.",
                "minimum": 1,
                "maximum": 1000,
            },
            "max_pages": {
                "type": "integer",
                "description": (
                    "Safety cap on number of pages to fetch. Defaults to 1000. "
                    "Set lower to bound response size/time."
                ),
                "minimum": 1,
                "maximum": 10000,
            },
            "closes_within_days": {
                "type": "integer",
                "description": "Only markets that close within this many days (default 8: this week's games).",
                "minimum": 1,
                "maximum": 365,
            },
            "max_markets": {
                "type": "integer",
                "description": "At most this many markets, the busiest by 24h volume (default 60); more_markets says how many were left out.",
                "minimum": 1,
                "maximum": 500,
            },
        },
        "required": ["series_ticker"],
        "additionalProperties": False,
    },
}

GET_OPEN_MARKET_TITLES_FOR_SERIES_TOOL = {
    "name": "get_open_market_titles_for_series",
    "description": (
        "The titles of every open Kalshi market in one series, to find the right market ticker without the price detail."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "series_ticker": {
                "type": "string",
                "description": "Series ticker to filter markets by.",
                "minLength": 1,
            },
            "limit": {
                "type": "integer",
                "description": "Optional page size for each /markets request (1-1000). Defaults to 1000.",
                "minimum": 1,
                "maximum": 1000,
            },
            "max_pages": {
                "type": "integer",
                "description": (
                    "Safety cap on number of pages to fetch. Defaults to 1000. "
                    "Set lower to bound response size/time."
                ),
                "minimum": 1,
                "maximum": 10000,
            },
        },
        "required": ["series_ticker"],
        "additionalProperties": False,
    },
}

GET_SUBACCOUNT_BALANCES_TOOL = {
    "name": "get_subaccount_balances",
    "description": (
        "The user's own Kalshi subaccount balances (needs their read-only API key)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}

GET_ORDERS_TOOL = {
    "name": "get_orders",
    "description": (
        "The user's own Kalshi orders (needs their read-only API key)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Filter by market ticker.",
                "minLength": 1,
            },
            "event_ticker": {
                "type": "string",
                "description": "Comma-separated event tickers to filter (maximum 10).",
                "minLength": 1,
            },
            "min_ts": {
                "type": "integer",
                "description": "Filter orders after this Unix timestamp.",
                "minimum": 0,
            },
            "max_ts": {
                "type": "integer",
                "description": "Filter orders before this Unix timestamp.",
                "minimum": 0,
            },
            "status": {
                "type": "string",
                "description": "Filter by order status.",
                "enum": ["resting", "canceled", "executed"],
            },
            "limit": {
                "type": "integer",
                "description": "Number of results per page (1-200). Defaults to 100.",
                "minimum": 1,
                "maximum": 200,
            },
            "cursor": {
                "type": "string",
                "description": "Pagination cursor.",
                "minLength": 1,
            },
            "subaccount": {
                "type": "integer",
                "description": "Subaccount number (0 for primary, 1-32 for subaccounts).",
                "minimum": 0,
                "maximum": 32,
            },
        },
        "additionalProperties": False,
    },
}

GET_ORDER_TOOL = {
    "name": "get_order",
    "description": (
        "One of the user's own Kalshi orders by its id (needs their read-only API key)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The order identifier.",
                "minLength": 1,
            },
        },
        "required": ["order_id"],
        "additionalProperties": False,
    },
}

GET_POSITIONS_TOOL = {
    "name": "get_positions",
    "description": (
        "The user's own Kalshi positions and their value (needs their read-only API key)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "cursor": {
                "type": "string",
                "description": "Pagination cursor.",
                "minLength": 1,
            },
            "limit": {
                "type": "integer",
                "description": "Number of results per page (1-1000).",
                "minimum": 1,
                "maximum": 1000,
            },
            "count_filter": {
                "type": "string",
                "description": (
                    "Comma-separated fields that must be non-zero. "
                    "Allowed values: position, total_traded."
                ),
            },
            "ticker": {
                "type": "string",
                "description": "Filter by market ticker.",
                "minLength": 1,
            },
            "event_ticker": {
                "type": "string",
                "description": "Filter by event ticker (or comma-separated list, maximum 10).",
                "minLength": 1,
            },
            "subaccount": {
                "type": "integer",
                "description": "Subaccount number (0 for primary, 1-32 for subaccounts).",
                "minimum": 0,
                "maximum": 32,
            },
        },
        "additionalProperties": False,
    },
}

GET_SERIES_TICKERS_FOR_CATEGORY_TOOL = {
    "name": "get_series_tickers_for_category",
    "description": (
        "Every Kalshi series ticker in one category COORDINATOR covers (sports, economics, crypto, tech, finance and politics)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Exact Kalshi series category name.",
                "minLength": 1,
            },
            "tags": {
                "type": "string",
                "description": "Optional tags filter (same meaning as /series?tags=...).",
                "minLength": 1,
            },
            "limit": {
                "type": "integer",
                "description": "Optional page size for each /series request (1-1000). Defaults to 1000.",
                "minimum": 1,
                "maximum": 1000,
            },
            "max_pages": {
                "type": "integer",
                "description": (
                    "Safety cap on number of pages to fetch. Defaults to 1000. "
                    "Set lower to bound response size/time."
                ),
                "minimum": 1,
                "maximum": 10000,
            },
        },
        "required": ["category"],
        "additionalProperties": False,
    },
}
